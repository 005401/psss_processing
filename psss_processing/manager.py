from threading import Event, Thread

from logging import getLogger

from copy import deepcopy

from psen_processing import config
from psen_processing.utils import validate_roi

_logger = getLogger(__name__)


class ProcessingManager(object):

    def __init__(self, stream_processor, roi_signal=None, roi_background=None, auto_start=False):

        self.stream_processor = stream_processor
        self.auto_start = auto_start

        if roi_background is None:
            roi_background = config.DEFAULT_ROI_BACKGROUND or []
        self.roi_background = roi_background

        if roi_signal is None:
            roi_signal = config.DEFAULT_ROI_SIGNAL or []
        self.roi_signal = roi_signal

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
                                        args=(self.running_flag, self.roi_signal, self.roi_background, self.statistics))

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

    def set_roi_background(self, roi_background):

        if not roi_background:
            roi_background = []

        validate_roi(roi_background)

        _logger.info("Setting ROI background to %s.", roi_background)

        self.roi_background.clear()
        self.roi_background.extend(roi_background)

    def set_roi_signal(self, roi_signal):

        if not roi_signal:
            roi_signal = []

        validate_roi(roi_signal)

        _logger.info("Setting ROI signal to %s.", roi_signal)

        self.roi_signal.clear()
        self.roi_signal.extend(roi_signal)

    def get_roi_background(self):
        return self.roi_background

    def get_roi_signal(self):
        return self.roi_signal

    def get_statistics(self):
        return deepcopy(self.statistics)

    def _is_running(self):
        return self.processing_thread and self.processing_thread.is_alive()

    def get_status(self):
        if self._is_running():
            return "processing"
        else:
            return "stopped"
