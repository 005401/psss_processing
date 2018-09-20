import unittest
from time import sleep

import numpy
from bsread.sender import sender
from multiprocessing import Process, Event
from bsread import source, PULL, json

from psss_processing import config
from psss_processing.processor import get_stream_processor, manipulate_image, process_image


class TestProcessing(unittest.TestCase):
    def test_manipulate_image(self):

        image = numpy.zeros(shape=(1024, 512), dtype="uint16")
        image += 1

        self.assertEqual(manipulate_image(image, None, 0, 0, 0).shape, (1024, 512))
        self.assertEqual(manipulate_image(image, None, 0, 0, 90).shape, (512, 1024))

        new_shape = manipulate_image(image, None, 0, 0, 45).shape
        # Rotating by 45 degree should always give you a square.
        self.assertEqual(new_shape[0], new_shape[1])
        # The threshold should remove all data.
        self.assertEqual(manipulate_image(image, None, 2, 0, 0).sum(), 0)

        roi = [200, 300, 200, 150]
        self.assertEqual(manipulate_image(image, roi, 0, 0, 45).shape, (150, 300))

    def test_process_image(self):
        image = numpy.zeros(shape=(1024, 512), dtype="uint16")
        image += 1

        image_property_name = "TESTING_IMAGE"

        roi = [0, 512, 0, 1024]

        image, processed_data = process_image(image, image_property_name, roi, 15, 30, 90)
        self.assertSetEqual(set(processed_data.keys()), {image_property_name + ".processing_parameters",
                                                         image_property_name + ".spectrum",
                                                         image_property_name})

        # After rotating for 90 degrees this is the largest image we can get for the ROI.
        self.assertEqual(image.shape, (512, 512))

        self.assertEqual(len(processed_data[image_property_name + ".spectrum"]), 512)

        processing_parameters = json.loads(processed_data[image_property_name + ".processing_parameters"])

        self.assertEqual(processing_parameters["min_threshold"], 15)
        self.assertEqual(processing_parameters["max_threshold"], 30)
        self.assertEqual(processing_parameters["rotation"], 90)
        self.assertListEqual(processing_parameters["roi"], roi)

    def test_stream_processor(self):
        pv_name_prefix = "JUST_TESTING"
        n_images = 5
        original_roi = [100, 300, 100, 200]
        original_parameters = {"min_threshold": 0,
                               "max_threshold": 0,
                               "rotation": 90}

        image = numpy.zeros(shape=(1024, 512), dtype="uint16")
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

        with source(host="localhost", port=11000, mode=PULL) as input_stream:
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
        self.assertEqual({"min_threshold": processing_parameters["min_threshold"],
                         "rotation": processing_parameters["rotation"],
                          "max_threshold": processing_parameters["max_threshold"]}, original_parameters)

        spectrum = final_data[0].data.data[pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE + ".spectrum"].value

        self.assertEqual(len(spectrum), 300)
        self.assertListEqual(list(spectrum), [200] * 300)
