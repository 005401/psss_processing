import os
import unittest
from time import sleep

import numpy
from bsread.sender import sender
from bsread import source, PULL, json
from multiprocessing import Process

from psss_processing import PsssProcessingClient, config
from psss_processing.start_processing import start_processing


class TestClient(unittest.TestCase):

    def setUp(self):
        self.n_images = 5
        self.pv_name_prefix = "JUST_TESTING"

        self.image = numpy.zeros(shape=(1024, 1024), dtype="uint16")
        self.image += 1

        data_to_send = {self.pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE: self.image}

        def send_data():
            with sender(port=10001) as output_stream:
                sleep(1)
                for x in range(self.n_images):
                    output_stream.send(data=data_to_send)

        def process_data():
            start_processing(input_stream="tcp://localhost:10001",
                             output_stream_port=12000,
                             rest_api_interface="0.0.0.0",
                             rest_api_port=10000,
                             epics_pv_name_prefix=self.pv_name_prefix,
                             output_pv="JUST_SOMETHING",
                             auto_start=False)

        self.sending_process = Process(target=send_data)
        self.processing_process = Process(target=process_data)

        self.sending_process.start()
        self.processing_process.start()
        sleep(1)

    def tearDown(self):
        if self.sending_process:
            self.sending_process.terminate()

        if self.processing_process:
            self.processing_process.terminate()

        if os.path.isfile("ignore_image.png"):
            os.remove("ignore_image.png")

        sleep(1)

    def test_classic_interaction(self):
        client = PsssProcessingClient("http://localhost:10000/")

        self.assertEqual(client.get_status(), "stopped")

        self.assertListEqual(client.get_roi(), [])
        self.assertDictEqual(client.get_parameters(), config.DEFAULT_PARAMETERS)

        client.set_roi(None)
        self.assertListEqual(client.get_roi(), [])

        with self.assertRaisesRegex(ValueError, "ROI offsets"):
            client.set_roi([-1, -1, -1, -1])

        roi = [0, 1024, 0, 1024]
        client.set_roi(roi)
        self.assertListEqual(client.get_roi(), roi)

        parameters = {"min_threshold": 10,
                      "max_threshold": 0,
                      "rotation": 45}
        client.set_parameters(parameters)
        self.assertDictEqual(client.get_parameters(), parameters)

        self.assertDictEqual(client.get_statistics(), {})

        client.start()
        self.assertEqual(client.get_status(), "processing")

        # Wait for PV connection timeout.
        sleep(1)

        statistics = client.get_statistics()
        self.assertEqual(len(statistics), 4)
        self.assertTrue("processing_start_time" in statistics)
        self.assertTrue("last_sent_pulse_id" in statistics)
        self.assertTrue("last_sent_time" in statistics)
        self.assertTrue("n_processed_images" in statistics)

        processed_data = []

        with source(host="localhost", port=12000, mode=PULL) as input_stream:
            for index in range(self.n_images-1):
                processed_data.append(input_stream.receive())

        statistics = client.get_statistics()

        self.assertEqual(statistics["n_processed_images"], self.n_images)

        # Pulse ids are 0 based.
        self.assertEqual(statistics["last_sent_pulse_id"], self.n_images - 1)

        self.assertTrue("processing_start_time" in statistics)
        self.assertTrue("last_sent_time" in statistics)
        self.assertTrue("image" not in statistics)

        self.assertEqual(client.get_status(), "processing")

        client.stop()
        self.assertEqual(client.get_status(), "stopped")

        client.start()
        self.assertEqual(client.get_status(), "processing")

        client.stop()
        self.assertEqual(client.get_status(), "stopped")

    def test_change_roi_while_running(self):
        client = PsssProcessingClient("http://localhost:10000/")

        roi = [0, 1024, 0, 1024]
        client.set_roi(roi)

        processed_data = []

        client.start()

        with source(host="localhost", port=12000, mode=PULL) as input_stream:
            # First pulse_id comes before the source connects.
            for index in range(self.n_images-1):
                message = input_stream.receive()
                processed_data.append(message)

        updated_roi = [100, 200, 100, 200]
        client.set_roi(updated_roi)

        data_to_send = {self.pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE: self.image}

        with sender(port=10001) as output_stream:
            for x in range(self.n_images):
                output_stream.send(data=data_to_send)

        with source(host="localhost", port=12000, mode=PULL) as input_stream:
            for index in range(self.n_images):
                message = input_stream.receive()
                processed_data.append(message)

        client.stop()

        processing_parameters_name = self.pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE + ".processing_parameters"

        start_processing_parameters = json.loads(processed_data[0].data.data[processing_parameters_name].value)
        end_processing_parameters = json.loads(processed_data[8].data.data[processing_parameters_name].value)

        self.assertListEqual(roi, start_processing_parameters["roi"])
        self.assertListEqual(updated_roi, end_processing_parameters["roi"])

    def test_no_roi(self):
        client = PsssProcessingClient("http://localhost:10000/")

        roi = []
        client.set_roi(roi)

        client.start()

        processed_data = []

        with source(host="localhost", port=12000, mode=PULL, receive_timeout=100) as input_stream:
            message = None
            while message is None:
                message = input_stream.receive()

        client.stop()

        spectrum_parameter_name = self.pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE + ".spectrum"

        # If the roi is not set, the value should not be added to the output.
        self.assertTrue(spectrum_parameter_name in message.data.data)

    def test_stop_when_blocking_send(self):
        client = PsssProcessingClient("http://localhost:10000/")

        client.start()

        def stop_client():
            client = PsssProcessingClient("http://localhost:10000/")
            client.stop()

        stop_process = Process(target=stop_client)
        stop_process.start()

        sleep(1)

        if stop_process.is_alive() and not stop_process.join(timeout=3):
            stop_process.terminate()
            raise ValueError("The stop call is blocked.")

    def test_download_image(self):
        client = PsssProcessingClient("http://localhost:10000/")

        with self.assertRaisesRegex(ValueError, "No image was processed yet"):
            client.get_last_processed_image("ignore_image.png")

        client.start()

        sleep(2)

        client.get_last_processed_image("ignore_image.png")

        self.assertTrue(os.path.isfile("ignore_image.png"))

        client.stop()
