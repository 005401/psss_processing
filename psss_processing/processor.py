import datetime
import json
import math
from logging import getLogger

import numba
import numpy
from bsread import source, PULL
from bsread.sender import sender
from zmq import Again
import epics
from epics import PV

from psss_processing import config

_logger = getLogger(__name__)


@numba.njit(parallel=True)
def calculate_summation_matrix(summation_matrix, rotation_angle):
    size_y, size_x = summation_matrix.shape
    # Rotation in radians in counter-clockwise direction.
    radian_angle = math.radians(rotation_angle)

    cos_angle = math.cos(radian_angle)
    sin_angle = math.sin(radian_angle)

    min_value = 0
    max_value = 0

    for y in numba.prange(size_y):
        for x in numba.prange(size_x):
            current_pixel_value = round((x * cos_angle) + (y * sin_angle))
            summation_matrix[y, x] = current_pixel_value

            min_value = min(min_value, current_pixel_value)
            max_value = max(max_value, current_pixel_value)

    # min_offset cannot be more than 0.
    summation_matrix -= min_value
    sum_length = max_value - min_value

    return summation_matrix, sum_length + 1


cached_sm_size_x = None
cached_sm_size_y = None
cached_sm_rotation = None
cached_sm = None
cached_sm_length = None


def get_summation_matrix(size_y, size_x, rotation):
    global cached_sm_size_x, cached_sm_size_y, cached_sm_rotation, cached_sm, cached_sm_length

    # When any of the parameters do not match we need to re-calculate the rotation matrix.
    if size_x != cached_sm_size_x or size_y != cached_sm_size_y or rotation != cached_sm_rotation:
        cached_sm_size_x = size_x
        cached_sm_size_y = size_y
        cached_sm_rotation = rotation

        cached_sm, cached_sm_length = calculate_summation_matrix(numpy.zeros(shape=(size_y, size_x), dtype="int16"),
                                                                 rotation)

    return cached_sm, cached_sm_length


@numba.njit(parallel=True)
def calculate_spectrum(image, min_threshold, max_threshold, summation_matrix, spectrum_length):
    min_threshold = int(min_threshold)
    max_threshold = int(max_threshold)

    size_y = image.shape[0]
    size_x = image.shape[1]

    spectrum_2d = numpy.zeros(shape=(size_y, spectrum_length), dtype=numpy.uint16)

    for y in numba.prange(size_y):
        for x in numba.prange(size_x):
            pixel_value = image[y, x]

            if pixel_value < min_threshold:
                continue

            elif 0 < max_threshold < pixel_value:
                continue

            spectrum_index = summation_matrix[y, x]
            spectrum_2d[y, spectrum_index] += pixel_value

    return spectrum_2d.sum(0).astype(numpy.uint32)


def process_image(image, image_property_name, roi, min_threshold, max_threshold, rotation):
    processed_data = dict()

    processed_data[image_property_name] = image
    processed_data[image_property_name + ".processing_parameters"] = json.dumps({"roi": roi,
                                                                                 "min_threshold": min_threshold,
                                                                                 "max_threshold": max_threshold,
                                                                                 "rotation": rotation})

    processing_image = numpy.array(image)

    if roi:
        offset_x, size_x, offset_y, size_y = roi
        processing_image = processing_image[offset_y:offset_y + size_y, offset_x:offset_x + size_x]

    size_y = processing_image.shape[0]
    size_x = processing_image.shape[1]

    summation_matrix, spectrum_length = get_summation_matrix(size_y, size_x, rotation)

    spectrum = calculate_spectrum(processing_image, min_threshold, max_threshold, summation_matrix, spectrum_length)

    processed_data[image_property_name + ".spectrum"] = spectrum

    return processed_data


def get_stream_processor(input_stream_host, input_stream_port, output_stream_port, epics_pv_name_prefix,
                         output_pv_name):
    def stream_processor(running_flag, roi, parameters, statistics):
        try:
            running_flag.set()

            _logger.info("Connecting to input_stream_host %s and input_stream_port %s.",
                         input_stream_host, input_stream_port)

            _logger.info("Sending out data on stream port %s.", output_stream_port)

            if output_pv_name:
                _logger.info("Sending out data on EPICS PV %s.", output_pv_name)
                epics.ca.clear_cache()
                output_pv = PV(output_pv_name)
            else:
                _logger.warning("Output EPICS PV not specified. Only bsread will be sent out.")

            with source(host=input_stream_host, port=input_stream_port, mode=PULL,
                        queue_size=config.INPUT_STREAM_QUEUE_SIZE,
                        receive_timeout=config.INPUT_STREAM_RECEIVE_TIMEOUT) as input_stream:

                with sender(port=output_stream_port, send_timeout=config.OUTPUT_STREAM_SEND_TIMEOUT,
                            block=False) as output_stream:

                    statistics["processing_start_time"] = str(datetime.datetime.now())
                    statistics["last_sent_pulse_id"] = None
                    statistics["last_sent_time"] = None
                    statistics["last_calculated_spectrum"] = None
                    statistics["n_processed_images"] = 0

                    image_property_name = epics_pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE

                    _logger.info("Using image_to_process property name '%s'.", image_property_name)

                    while running_flag.is_set():

                        message = input_stream.receive()

                        if message is None:
                            continue

                        pulse_id = message.data.pulse_id
                        timestamp = (message.data.global_timestamp, message.data.global_timestamp_offset)

                        _logger.debug("Received message with pulse_id %s", pulse_id)

                        image_to_process = message.data.data[image_property_name].value

                        processed_data = process_image(image_to_process,
                                                       image_property_name,
                                                       roi,
                                                       parameters["min_threshold"],
                                                       parameters["max_threshold"],
                                                       parameters["rotation"])

                        try:
                            output_stream.send(pulse_id=pulse_id,
                                               timestamp=timestamp,
                                               data=processed_data)

                            _logger.debug("Sent message with pulse_id %s", pulse_id)

                            statistics["last_sent_pulse_id"] = pulse_id
                            statistics["last_sent_time"] = str(datetime.datetime.now())
                        except Again:
                            pass

                        statistics["last_calculated_spectrum"] = processed_data[image_property_name + ".spectrum"]
                        statistics["n_processed_images"] = statistics.get("n_processed_images", 0) + 1

                        if output_pv_name:
                            output_pv.put(processed_data[image_property_name + ".spectrum"])
                            _logger.debug("caput on %s for pulse_id %s", output_pv, pulse_id)

        except Exception as e:
            _logger.error("Error while processing the stream. Exiting. Error: ", e)
            running_flag.clear()

            raise

        except KeyboardInterrupt:
            _logger.warning("Terminating processing due to user request.")
            running_flag.clear()

            raise

    return stream_processor
