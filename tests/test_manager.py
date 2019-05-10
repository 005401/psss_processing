import unittest
from time import sleep

from psss_processing import config
from psss_processing.manager import ProcessingManager


class TestProcessingManager(unittest.TestCase):

    def test_standard_workflow(self):
        test_parameters = {}

        def processor(running_flag, parameters, statistics):
            nonlocal test_parameters

            running_flag.set()

            while running_flag.is_set():

                test_parameters = parameters

                statistics["counter"] = statistics.get("counter", 0) + 1

                sleep(0.01)

        manager = None

        try:
            manager = ProcessingManager(processor, auto_start=False)

            self.assertEqual(manager.get_status(), "stopped")

            manager.start()

            self.assertTrue(manager.running_flag.is_set())
            self.assertEqual(manager.get_status(), "processing")

            parameters = {"background": ""}
            manager.set_parameters(parameters)
            sleep(0.1)
            self.assertDictEqual(test_parameters, parameters)

            manager.stop()
            self.assertEqual(manager.get_status(), "stopped")

            self.assertGreater(manager.get_statistics()["counter"], 0)

        except:
            if manager:
                manager.stop()

            raise

    def test_exception_when_starting(self):

        def processor(running_flag, parameters, statistics):
            sleep(config.PROCESSOR_START_TIMEOUT + 0.2)

        with self.assertRaisesRegex(RuntimeError, "Cannot start processing"):
            ProcessingManager(processor, auto_start=True)

        manager = ProcessingManager(processor)
        self.assertEqual(manager.get_status(), "stopped")

        with self.assertRaisesRegex(RuntimeError, "Cannot start processing"):
            manager.start()

        self.assertEqual(manager.get_status(), "stopped")
