import unittest
from time import sleep

import numpy
from bsread.sender import sender
from multiprocessing import Process, Event
from bsread import source, PULL, json

from psss_processing import config
from psss_processing.processor import get_stream_processor


class TestProcessing(unittest.TestCase):
    def test_get_roi_x_profile(self):
        image = numpy.zeros(shape=(1024, 1024), dtype="uint16")
        image += 1

        roi = [0, 1024, 0, 1024]
        x_profile = get_roi_x_profile(image, roi)

        self.assertEqual(len(x_profile), 1024)
        self.assertListEqual(list(x_profile), [1024] * 1024)

        roi = [0, 100, 0, 1024]
        x_profile = get_roi_x_profile(image, roi)

        self.assertEqual(len(x_profile), 100)
        self.assertListEqual(list(x_profile), [1024] * 100)

        roi = [0, 100, 0, 100]
        x_profile = get_roi_x_profile(image, roi)

        self.assertEqual(len(x_profile), 100)
        self.assertListEqual(list(x_profile), [100] * 100)

    def test_process_image(self):
        image = numpy.zeros(shape=(1024, 1024), dtype="uint16")
        image += 1

        image_property_name = "TESTING_IMAGE"

        roi_signal = [0, 1024, 0, 1024]
        roi_background = []

        processed_data = process_image(image, image_property_name, roi_signal, roi_background)

        self.assertSetEqual(set(processed_data.keys()), {image_property_name + ".processing_parameters",
                                                         image_property_name + ".roi_signal_x_profile"})

        roi_signal = [0, 1024, 0, 1024]
        roi_background = [0, 100, 0, 100]

        processed_data = process_image(image, image_property_name, roi_signal, roi_background)

        self.assertSetEqual(set(processed_data.keys()), {image_property_name + ".processing_parameters",
                                                         image_property_name + ".roi_signal_x_profile",
                                                         image_property_name + ".roi_background_x_profile"})

        self.assertEqual(len(processed_data[image_property_name + ".roi_signal_x_profile"]), 1024)
        self.assertListEqual(list(processed_data[image_property_name + ".roi_signal_x_profile"]), [1024] * 1024)

        self.assertEqual(len(processed_data[image_property_name + ".roi_background_x_profile"]), 100)
        self.assertListEqual(list(processed_data[image_property_name + ".roi_background_x_profile"]), [100] * 100)

    def test_stream_processor(self):
        pv_name_prefix = "JUST_TESTING"
        n_images = 5
        original_roi = [0, 1024, 0, 512]
        original_parameters = {"threshold": 0,
                               "rotation": 0}

        image = numpy.zeros(shape=(1024, 1024), dtype="uint16")
        image += 1

        data_to_send = {pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE: image}

        def send_data():
            with sender(port=10000) as output_stream:
                for x in range(n_images):
                    output_stream.send(data=data_to_send)

        def process_data(event):
            stream_processor = get_stream_processor(input_stream_host="localhost",
                                                    input_stream_port=10000,
                                                    output_stream_port=11000,
                                                    epics_pv_name_prefix=pv_name_prefix,
                                                    output_pv_name="Does not matter")

            stream_processor(event, original_roi, original_parameters, {})

        running_event = Event()

        send_process = Process(target=send_data)
        processing_process = Process(target=process_data, args=(running_event,))

        send_process.start()
        processing_process.start()

        final_data = []

        with source(host="localhost", port=11000, mode=PULL, receive_timeout=1000) as input_stream:
            for _ in range(n_images):
                final_data.append(input_stream.receive())

        running_event.clear()

        sleep(0.2)

        send_process.terminate()
        processing_process.terminate()

        self.assertEqual(len(final_data), n_images)

        parameters = final_data[0].data.data[pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE +
                                             ".processing_parameters"].value
        processing_parameters = json.loads(parameters)

        self.assertEqual(processing_parameters["roi"], original_roi)
        self.assertEqual({"threshold": processing_parameters["threshold"],
                         "rotation": processing_parameters["rotation"]}, original_parameters)

        spectrum = final_data[0].data.data[pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE + ".spectrum"].value

        self.assertEqual(len(spectrum), 1024)
        self.assertListEqual(list(spectrum), [512] * 1024)
