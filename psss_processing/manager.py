from threading import Event, Thread

from logging import getLogger

from copy import deepcopy

from psss_processing import config
from psss_processing.utils import validate_roi

_logger = getLogger(__name__)


class ProcessingManager(object):

    def __init__(self, stream_processor, roi=None, parameters=None, auto_start=False):

        self.stream_processor = stream_processor
        self.auto_start = auto_start

        if roi is None:
            roi = config.DEFAULT_ROI
        self.roi = roi

        if parameters is None:
            parameters = config.DEFAULT_PARAMETERS
        self.parameters = parameters

        self.processing_thread = None
        self.running_flag = None

        self.statistics = {}

        if auto_start:
            self.start()

    def start(self):

        if self._is_running():
            _logger.debug("Trying to start an already running stream_processor.")
            return

        self.running_flag = Event()

        self.processing_thread = Thread(target=self.stream_processor,
                                        args=(self.running_flag, self.roi, self.parameters, self.statistics))

        self.processing_thread.start()

        if not self.running_flag.wait(timeout=config.PROCESSOR_START_TIMEOUT):
            self.stop()

            raise RuntimeError("Cannot start processing thread in time. Please check error log for more info.")

    def stop(self):

        if self._is_running():
            self.running_flag.clear()
            self.processing_thread.join()

        self.processing_thread = None
        self.running_flag = None

    def set_roi(self, roi):

        if not roi:
            roi = []

        validate_roi(roi)

        _logger.info("Setting ROI to %s.", roi)

        self.roi.clear()
        self.roi.extend(roi)

    def set_parameters(self, parameters):

        self.parameters["min_threshold"] = parameters.get("min_threshold", 0)
        self.parameters["max_threshold"] = parameters.get("max_threshold", 0)
        self.parameters["rotation"] = parameters.get("rotation", 0)

    def get_roi(self):
        return self.roi

    def get_parameters(self):
        return self.parameters

    def get_statistics(self):
        result = deepcopy(self.statistics)

        if "last_sent_image" in result:
            del result["last_sent_image"]

        return result

    def get_last_processed_image(self):
        return self.statistics.get("last_sent_image")

    def _is_running(self):
        return self.processing_thread and self.processing_thread.is_alive()

    def get_status(self):
        if self._is_running():
            return "processing"
        else:
            return "stopped"
