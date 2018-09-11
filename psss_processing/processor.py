import datetime
import json
from logging import getLogger

from bsread import source, PULL
from bsread.sender import sender
from epics import PV
from scipy import ndimage
from zmq import Again

from psss_processing import config

_logger = getLogger(__name__)


def manipulate_image(image, roi, threshold, rotation):

    if threshold > 0:
        image[image < int(threshold)] = 0

    if rotation != 0:
        image = ndimage.rotate(image, angle=rotation)

    if roi:
        offset_x, size_x, offset_y, size_y = roi
        image = image[offset_y:offset_y + size_y, offset_x:offset_x + size_x]

    return image


def process_image(image, image_property_name, roi, threshold, rotation):
    processed_data = dict()

    processed_data[image_property_name + ".processing_parameters"] = json.dumps({"roi": roi,
                                                                                 "threshold": threshold,
                                                                                 "rotation": rotation})

    image = manipulate_image(image, roi, threshold, rotation)

    processed_data[image_property_name + ".spectrum"] = image.sum(0)

    return image, processed_data


def get_stream_processor(input_stream_host, input_stream_port, output_stream_port, epics_pv_name_prefix,
                         output_pv_name):

    def stream_processor(running_flag, roi, parameters, statistics):
        try:
            running_flag.set()

            _logger.info("Connecting to input_stream_host %s and input_stream_port %s.",
                         input_stream_host, input_stream_port)

            _logger.info("Sending out data on stream port %s.", output_stream_port)
            _logger.info("Sending out data on EPICS PV %s.", output_pv_name)

            output_pv = PV(output_pv_name)

            with source(host=input_stream_host, port=input_stream_port, mode=PULL,
                        queue_size=config.INPUT_STREAM_QUEUE_SIZE,
                        receive_timeout=config.INPUT_STREAM_RECEIVE_TIMEOUT) as input_stream:

                with sender(port=output_stream_port, send_timeout=config.OUTPUT_STREAM_SEND_TIMEOUT) as output_stream:

                    statistics["processing_start_time"] = str(datetime.datetime.now())
                    statistics["last_sent_pulse_id"] = None
                    statistics["last_sent_time"] = None
                    statistics["last_sent_image"] = None
                    statistics["n_processed_images"] = 0

                    image_property_name = epics_pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE

                    _logger.info("Using image property name '%s'.", image_property_name)

                    while running_flag.is_set():

                        message = input_stream.receive()

                        if message is None:
                            continue

                        pulse_id = message.data.pulse_id
                        timestamp = (message.data.global_timestamp, message.data.global_timestamp_offset)

                        _logger.debug("Received message with pulse_id %s", pulse_id)

                        image = message.data.data[image_property_name].value

                        image, processed_data = process_image(image, image_property_name,
                                                              roi, parameters["threshold"], parameters["rotation"])

                        try:
                            output_stream.send(pulse_id=pulse_id,
                                               timestamp=timestamp,
                                               data=processed_data)

                            _logger.debug("Sent message with pulse_id %s", pulse_id)

                            output_pv.put(processed_data[image_property_name + ".spectrum"])
                            _logger.debug("caput on %s for pulse_id %s", output_pv, pulse_id)

                            statistics["last_sent_pulse_id"] = pulse_id
                            statistics["last_sent_time"] = str(datetime.datetime.now())
                            statistics["last_sent_image"] = image
                            statistics["n_processed_images"] = statistics.get("n_processed_images", 0) + 1

                        except Again:
                            pass

                        except Exception as e:
                            _logger.error("Cannot send out the spectrum.", e)

        except Exception as e:
            _logger.error("Error while processing the stream. Exiting. Error: ", e)
            running_flag.clear()

            raise

        except KeyboardInterrupt:
            _logger.warning("Terminating processing due to user request.")
            running_flag.clear()

            raise

    return stream_processor
