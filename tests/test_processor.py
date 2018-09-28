import unittest
from time import sleep

import numpy
from bsread.sender import sender
from multiprocessing import Process, Event
from bsread import source, PULL, json
from scipy import ndimage

from psss_processing import config
from psss_processing.processor import get_stream_processor, process_image, calculate_summation_matrix, \
    calculate_spectrum


class TestProcessing(unittest.TestCase):

    def test_process_image(self):
        image = numpy.zeros(shape=(1024, 512), dtype="uint16")
        image += 1

        image_property_name = "TESTING_IMAGE"

        roi = [0, 512, 0, 1024]

        processed_data = process_image(image, image_property_name, roi, 15, 30, 90)
        self.assertSetEqual(set(processed_data.keys()), {image_property_name + ".processing_parameters",
                                                         image_property_name + ".spectrum",
                                                         image_property_name})

        # Original image should not be manipulated
        self.assertEqual(image.shape, (1024, 512))

        self.assertEqual(len(processed_data[image_property_name + ".spectrum"]), 1024)

        processing_parameters = json.loads(processed_data[image_property_name + ".processing_parameters"])

        self.assertEqual(processing_parameters["min_threshold"], 15)
        self.assertEqual(processing_parameters["max_threshold"], 30)
        self.assertEqual(processing_parameters["rotation"], 90)
        self.assertListEqual(processing_parameters["roi"], roi)

    def test_stream_processor(self):
        pv_name_prefix = "JUST_TESTING"
        n_images = 50
        original_roi = [100, 300, 100, 200]
        original_parameters = {"min_threshold": 0,
                               "max_threshold": 0,
                               "rotation": 90}

        image = numpy.zeros(shape=(1024, 512), dtype="uint16")
        image += 1

        data_to_send = {pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE: image}

        def send_data():
            with sender(port=10000, queue_size=100) as output_stream:
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
        sleep(1)
        processing_process.start()

        final_data = []

        with source(host="localhost", port=11000, mode=PULL) as input_stream:
            final_data.append(input_stream.receive())

        running_event.clear()

        sleep(0.2)

        send_process.terminate()
        processing_process.terminate()

        self.assertEqual(len(final_data), 1)

        parameters = final_data[0].data.data[pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE +
                                             ".processing_parameters"].value
        processing_parameters = json.loads(parameters)

        self.assertEqual(processing_parameters["roi"], original_roi)
        self.assertEqual({"min_threshold": processing_parameters["min_threshold"],
                         "rotation": processing_parameters["rotation"],
                          "max_threshold": processing_parameters["max_threshold"]}, original_parameters)

        spectrum = final_data[0].data.data[pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE + ".spectrum"].value

        self.assertEqual(len(spectrum), 200)
        self.assertListEqual(list(spectrum), [300] * 200)

    def test_max_threshold(self):
        image = numpy.zeros(shape=(1024, 512), dtype="uint16")
        image += 50

        self.assertTrue(process_image(image, "test", None, 0, 50, 0)["test.spectrum"].sum() > 0)
        self.assertTrue(process_image(image, "test", None, 0, 51, 0)["test.spectrum"].sum() > 0)
        self.assertTrue(process_image(image, "test", None, 0, 49, 0)["test.spectrum"].sum() == 0)

    def test_calculate_summation_matrix(self):
        size_y = 512
        size_x = 1024
        summation_matrix = numpy.zeros(shape=(size_y, size_x), dtype="int16")

        _, sum_length = calculate_summation_matrix(summation_matrix, 0)
        self.assertEqual(sum_length, size_x)
        for y in range(size_y):
            for x in range(size_x):
                # 0 degree rotation = vertical summation.
                self.assertEqual(summation_matrix[y, x], x)

        _, sum_length = calculate_summation_matrix(summation_matrix, 180)
        self.assertEqual(sum_length, size_x)
        for y in range(size_y):
            for x in range(size_x):
                # 180 degree rotation = vertical summation from right to left.
                self.assertEqual(summation_matrix[y, x], (size_x-1) - x)

        _, sum_length = calculate_summation_matrix(summation_matrix, -180)
        self.assertEqual(sum_length, size_x)
        for y in range(size_y):
            for x in range(size_x):
                # -180 degree rotation = vertical summation from right to left.
                self.assertEqual(summation_matrix[y, x], (size_x - 1) - x)

        _, sum_length = calculate_summation_matrix(summation_matrix, 90)
        self.assertEqual(sum_length, size_y)
        for y in range(size_y):
            for x in range(size_x):
                # 90 degree rotation = invert columns and rows.
                self.assertEqual(summation_matrix[y, x], y)

        _, sum_length = calculate_summation_matrix(summation_matrix, -90)
        self.assertEqual(sum_length, size_y)
        for y in range(size_y):
            for x in range(size_x):
                # 90 degree rotation = invert columns and rows, bottom to top.
                self.assertEqual(summation_matrix[y, x], (size_y-1) - y)

    def test_calculate_spectrum(self):
        size_x = 1024
        size_y = 512

        image = numpy.zeros(shape=(size_y, size_x), dtype="int32")
        summation_matrix = numpy.zeros(shape=(size_y, size_x), dtype="int16")

        image[200:400, 300:800] = 1

        numpy_spectrum = image.sum(0)

        _, sum_length = calculate_summation_matrix(summation_matrix, 0)
        numba_spectrum = calculate_spectrum(image, 0, 0, summation_matrix, sum_length)

        numpy.testing.assert_array_equal(numpy_spectrum, numba_spectrum)

    def test_fast_vs_normal_image_rotation(self):

        def compare_images(size_x, size_y, rotation_angle, diff_tolerance):

            image = numpy.zeros(shape=(size_y, size_x), dtype="int32")
            image[100:1000, 300:500] = 1

            rotated_image_spectrum = ndimage.rotate(image, angle=rotation_angle, order=0).sum(0).astype("uint32")
            processed_image_spectrum = process_image(image, "", None, 0, 0, rotation_angle)[".spectrum"]

            self.assertTrue(abs(rotated_image_spectrum.shape[0] - processed_image_spectrum.shape[0]) < 2)
            self.assertTrue(processed_image_spectrum.sum(), 18000)

            self.assertTrue(rotated_image_spectrum.max() < max(size_x, size_y) * 1.5)
            self.assertTrue(processed_image_spectrum.max() < max(size_x, size_y) * 1.5)

            spectrum_diff = rotated_image_spectrum.astype("int64") - processed_image_spectrum

            self.assertTrue(abs(spectrum_diff.max()) < diff_tolerance)
            self.assertTrue(abs(spectrum_diff.min()) < diff_tolerance)

            # import matplotlib.pyplot as plt
            # plt.plot(rotated_image_spectrum)
            # plt.show()
            #
            # plt.plot(processed_image_spectrum)
            # plt.show()

        test_cases = [
            # size_x, size_y, rotation_angle, diff_tolerance
            [1024, 512, 71, 5],
            [2048, 512, 14, 50],
            [2048, 2048, 45, 300]
        ]

        for case in test_cases:
            compare_images(*case)
