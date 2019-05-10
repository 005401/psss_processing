from threading import Event, Thread

from logging import getLogger

from copy import deepcopy

from psss_processing import config

_logger = getLogger(__name__)


class ProcessingManager(object):

    def __init__(self, stream_processor, parameters=None, auto_start=False):

        self.stream_processor = stream_processor
        self.auto_start = auto_start

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
                                        args=(self.running_flag, self.parameters, self.statistics))

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

    def set_parameters(self, parameters):
        self.parameters.update(parameters)

    def get_parameters(self):
        return self.parameters

    def get_statistics(self):
        result = deepcopy(self.statistics)

        if "last_calculated_spectrum" in result:
            del result["last_calculated_spectrum"]

        return result

    def _is_running(self):
        return self.processing_thread and self.processing_thread.is_alive()

    def get_status(self):
        if self._is_running():
            return "processing"
        else:
            return "stopped"
