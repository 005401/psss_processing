import datetime
import json
import logging

import numpy
import scipy.signal
import zmq
import epics

from bsread import source, PULL
from bsread.sender import sender

from psss_processing import config, functions

_logger = logging.getLogger(__name__)


def process_image(image, axis, epics_pv_name_prefix, roi, parameters):
    processed_data = dict()

    processed_data[epics_pv_name_prefix + ":processing_parameters"] = \
        json.dumps({"roi": roi, "background": parameters['background']})

    processing_image = image
    # validate background data
    background_image = parameters.get('background_data')
    if isinstance(background_image, numpy.ndarray):
        if background_image.shape != processing_image.shape:
            background_image = None
    else:
        background_image = None

    # crop the image in y direction
    ymin, ymax = roi
    if processing_image.shape[0] > ymax > ymin > 0:
        processing_image = processing_image[ymin:ymax, :]
        if background_image is not None:
            background_image = background_image[ymin:ymax, :]

    # remove the background and collapse in y direction to get the spectrum
    if background_image is not None:
        spectrum = functions.get_spectrum(processing_image, background_image)
    else:
        spectrum = processing_image.sum(0, 'uint32')

    # smooth the spectrum with savgol filter with 51 window size and 3rd order polynomial
    smoothed_spectrum = scipy.signal.savgol_filter(spectrum, 51, 3)

    # gaussian fitting
    offset, amplitude, center, sigma = functions.gauss_fit(smoothed_spectrum[::2], axis[::2])

    # outputs
    processed_data[epics_pv_name_prefix + ":SPECTRUM_Y"] = spectrum
    processed_data[epics_pv_name_prefix + ":SPECTRUM_X"] = axis
    processed_data[epics_pv_name_prefix + ":SPECTRUM_CENTER"] = center
    processed_data[epics_pv_name_prefix + ":SPECTRUM_FWHM"] = 2.355 * sigma

    return processed_data


def get_stream_processor(input_stream_host, input_stream_port, data_output_stream_port, image_output_stream_port,
                         epics_pv_name_prefix, output_pv_name, center_pv_name, fwhm_pv_name, ymin_pv_name,
                         ymax_pv_name, axis_pv_name):
    def stream_processor(running_flag, parameters, statistics):
        try:
            running_flag.set()

            _logger.info("Connecting to input_stream_host %s and input_stream_port %s.",
                         input_stream_host, input_stream_port)

            _logger.info("Sending out data on stream port %s.", data_output_stream_port)
            _logger.info("Sending out images on stream port %s.", image_output_stream_port)

            if output_pv_name:
                _logger.info("Sending out spectrum data on EPICS PV %s.", output_pv_name)
                epics.ca.clear_cache()
                output_pv = epics.PV(output_pv_name)
            else:
                _logger.warning("Output EPICS PV not specified. Only bsread will be sent out.")

            if center_pv_name:
                _logger.info("Sending out spectrum center on EPICS PV %s.", center_pv_name)
                center_pv = epics.PV(center_pv_name)
            else:
                _logger.warning("Output EPICS PV not specified. Only bsread will be sent out.")

            if fwhm_pv_name:
                _logger.info("Sending out spectrum fwhm on EPICS PV %s.", fwhm_pv_name)
                fwhm_pv = epics.PV(fwhm_pv_name)
            else:
                _logger.warning("Output EPICS PV not specified. Only bsread will be sent out.")
            # EPICS PV for vertical ROI
            if ymin_pv_name:
                ymin_pv = epics.PV(ymin_pv_name)
                ymin_pv.wait_for_connection()
            if ymax_pv_name:
                ymax_pv = epics.PV(ymax_pv_name)
                ymax_pv.wait_for_connection()
            if axis_pv_name:
                axis_pv = epics.PV(axis_pv_name)
                axis_pv.wait_for_connection()

            roi = [0, 0]

            with source(host=input_stream_host, port=input_stream_port, mode=PULL,
                        queue_size=config.INPUT_STREAM_QUEUE_SIZE,
                        receive_timeout=config.INPUT_STREAM_RECEIVE_TIMEOUT) as input_stream:

                with sender(port=data_output_stream_port, send_timeout=config.OUTPUT_STREAM_SEND_TIMEOUT,
                            block=False) as data_output_stream:

                    with sender(port=image_output_stream_port, send_timeout=config.OUTPUT_STREAM_SEND_TIMEOUT,
                                block=False, queue_size=config.IMAGE_OUTPUT_STREAM_QUEUE_SIZE) as image_output_stream:

                        statistics["processing_start_time"] = str(datetime.datetime.now())
                        statistics["last_sent_pulse_id"] = None
                        statistics["last_sent_time"] = None
                        statistics["last_calculated_spectrum"] = None
                        statistics["n_processed_images"] = 0

                        image_property_name = epics_pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE

                        _logger.info("Using image_to_process property name '%s'.", image_property_name)

                        while running_flag.is_set():

                            try:
                                message = input_stream.receive()
                            except:
                                _logger.exception("input stream receiving error")
                                continue

                            if message is None:
                                continue

                            pulse_id = message.data.pulse_id
                            timestamp = (message.data.global_timestamp, message.data.global_timestamp_offset)

                            _logger.debug("Received message with pulse_id %s", pulse_id)

                            image_to_process = message.data.data[image_property_name].value
                            image_data = {image_property_name: image_to_process}

                            if ymin_pv_name and ymin_pv.connected:
                                roi[0] = ymin_pv.value
                            if ymax_pv_name and ymax_pv.connected:
                                roi[1] = ymax_pv.value
                            if axis_pv_name and axis_pv.connected:
                                axis = axis_pv.value
                            else:
                                axis = None

                            if axis is None or len(axis) != image_to_process.shape[1]:
                                _logger.warn("Invalid energy axis")
                                continue

                            processed_data = process_image(image_to_process,
                                                           axis,
                                                           epics_pv_name_prefix,
                                                           roi,
                                                           parameters)

                            try:
                                data_output_stream.send(pulse_id=pulse_id,
                                                        timestamp=timestamp,
                                                        data=processed_data)

                                _logger.debug("Sent data message with pulse_id %s", pulse_id)

                                statistics["last_sent_pulse_id"] = pulse_id
                                statistics["last_sent_time"] = str(datetime.datetime.now())
                            except zmq.Again:
                                pass

                            try:
                                image_output_stream.send(pulse_id=pulse_id,
                                                         timestamp=timestamp,
                                                         data=image_data)

                                _logger.debug("Sent image message with pulse_id %s", pulse_id)
                            except zmq.Again:
                                pass

                            statistics["last_calculated_spectrum"] = processed_data[epics_pv_name_prefix +
                                                                                    ":SPECTRUM_Y"]
                            statistics["n_processed_images"] = statistics.get("n_processed_images", 0) + 1

                            if output_pv_name and output_pv.connected:
                                output_pv.put(processed_data[epics_pv_name_prefix + ":SPECTRUM_Y"])
                                _logger.debug("caput on %s for pulse_id %s", output_pv, pulse_id)

                            if center_pv_name and center_pv.connected:
                                center_pv.put(processed_data[epics_pv_name_prefix + ":SPECTRUM_CENTER"])

                            if fwhm_pv_name and fwhm_pv.connected:
                                fwhm_pv.put(processed_data[epics_pv_name_prefix + ":SPECTRUM_FWHM"])

        except Exception as e:
            _logger.error("Error while processing the stream. Exiting. Error: ", e)
            running_flag.clear()

            raise

        except KeyboardInterrupt:
            _logger.warning("Terminating processing due to user request.")
            running_flag.clear()

            raise

    return stream_processor
