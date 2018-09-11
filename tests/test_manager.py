import unittest
from time import sleep

from psss_processing import config
from psss_processing.manager import ProcessingManager
from psss_processing.utils import validate_roi


class TestProcessingManager(unittest.TestCase):

    def test_standard_workflow(self):
        test_roi = []
        test_parameters = {}

        def processor(running_flag, roi, parameters, statistics):
            nonlocal test_roi
            nonlocal test_parameters

            running_flag.set()

            while running_flag.is_set():

                test_roi = roi
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

            roi = [1, 2, 3, 4]
            manager.set_roi(roi)
            sleep(0.1)
            self.assertListEqual(test_roi, roi)

            parameters = {"threshold": 10,
                          "rotation": 5}
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

        def processor(running_flag, roi, parameters, statistics):
            sleep(config.PROCESSOR_START_TIMEOUT + 0.2)

        with self.assertRaisesRegex(RuntimeError, "Cannot start processing"):
            ProcessingManager(processor, auto_start=True)

        manager = ProcessingManager(processor)
        self.assertEqual(manager.get_status(), "stopped")

        with self.assertRaisesRegex(RuntimeError, "Cannot start processing"):
            manager.start()

        self.assertEqual(manager.get_status(), "stopped")

    def test_validate_roi(self):

        with self.assertRaisesRegex(ValueError, "ROI offsets"):
            validate_roi([-1, 0, 0, 0])

        with self.assertRaisesRegex(ValueError, "ROI sizes"):
            validate_roi([0, 1, 0, 0])

        validate_roi([0, 1, 0, 1])

        validate_roi([])

        with self.assertRaisesRegex(ValueError, "ROI must be an instance of a list"):
            validate_roi(None)
