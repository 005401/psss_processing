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
        self.client = PsssProcessingClient("http://localhost:10000/")

        self.n_images = 5
        self.pv_name_prefix = "JUST_TESTING"

        self.image = numpy.zeros(shape=(1024, 1024), dtype="uint16")
        self.image += 1

        data_to_send = {self.pv_name_prefix + config.EPICS_PV_SUFFIX_IMAGE: self.image}

        def send_data():
            with sender(port=10001, queue_size=100) as output_stream:
                sleep(1)
                for x in range(self.n_images):
                    output_stream.send(data=data_to_send)

        def process_data():
            start_processing(input_stream="tcp://localhost:10001",
                             output_stream_port=12000,
                             rest_api_interface="0.0.0.0",
                             rest_api_port=10000,
                             epics_pv_name_prefix=self.pv_name_prefix,
                             output_pv=None,
                             center_pv=None,
                             fwhm_pv=None,
                             ymin_pv=None,
                             ymax_pv=None,
                             axis_pv=None,
                             auto_start=False)

        self.sending_process = Process(target=send_data)
        self.processing_process = Process(target=process_data)

        self.sending_process.start()
        self.processing_process.start()
        sleep(1)

    def tearDown(self):
        try:
            self.client.stop()
        except:
            pass

        if self.sending_process:
            self.sending_process.terminate()

        if self.processing_process:
            self.processing_process.terminate()

        if os.path.isfile("ignore_image.png"):
            os.remove("ignore_image.png")

        sleep(2)

    def test_classic_interaction(self):
        client = PsssProcessingClient("http://localhost:10000/")

        self.assertEqual(client.get_status(), "stopped")

        self.assertDictEqual(client.get_parameters(), config.DEFAULT_PARAMETERS)

        client.set_background()
        self.assertDictEqual(client.get_parameters(), {"background": ""})

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
            processed_data.append(input_stream.receive())

        statistics = client.get_statistics()

        self.assertTrue(statistics["n_processed_images"] > 0)

        # Pulse ids are 0 based.
        self.assertTrue(statistics["last_sent_pulse_id"] > 0)

        self.assertTrue("processing_start_time" in statistics)
        self.assertTrue("last_sent_time" in statistics)

        self.assertEqual(client.get_status(), "processing")

        client.stop()
        self.assertEqual(client.get_status(), "stopped")

        client.start()
        self.assertEqual(client.get_status(), "processing")

        client.stop()
        self.assertEqual(client.get_status(), "stopped")

    def test_stop_when_blocking_send(self):
        client = PsssProcessingClient("http://localhost:10000/")

        client.start()

        def stop_client():
            client = PsssProcessingClient("http://localhost:10000/")
            client.stop()

        stop_process = Process(target=stop_client)
        stop_process.start()

        sleep(2)

        if stop_process.is_alive() and not stop_process.join(timeout=3):
            stop_process.terminate()
            raise ValueError("The stop call is blocked.")
