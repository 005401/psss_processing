import requests

from psen_processing import config


def validate_response(server_response):
    if server_response["state"] != "ok":
        raise ValueError(server_response.get("status", "Unknown error occurred."))

    return server_response


class PsenProcessingClient(object):
    def __init__(self, address="http://sf-daqsync-02:12000/"):
        """
        :param address: Address of the PSEN Processing service, e.g. http://localhost:11000
        """

        self.api_address_format = address.rstrip("/") + config.API_PREFIX + "%s"
        self.address = address

    def get_address(self):
        """
        Return the REST api endpoint address.
        """
        return self.address

    def start(self):
        """
        Start the processing.
        :return: Server status.
        """
        rest_endpoint = "/start"

        server_response = requests.post(self.api_address_format % rest_endpoint).json()
        return validate_response(server_response)["status"]

    def stop(self):
        """
        Stop the processing.
        :return: Server status.
        """
        rest_endpoint = "/stop"

        server_response = requests.post(self.api_address_format % rest_endpoint).json()
        return validate_response(server_response)["status"]

    def get_status(self):
        """
        Get the status of the processing.
        :return: Server status.
        """
        rest_endpoint = "/status"

        server_response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(server_response)["status"]

    def get_statistics(self):
        """
        Get the statistics of the processing.
        :return: Server statistics.
        """
        rest_endpoint = "/statistics"

        server_response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(server_response)["statistics"]

    def get_roi_signal(self):
        """
        Get the ROI for the signal.
        :return: Signal ROI as a list.
        """
        rest_endpoint = "/roi_signal"

        server_response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(server_response)["roi_signal"]

    def set_roi_signal(self, roi):
        """
        Set the ROI for the signal.
        :param roi: List of 4 elements: [offset_x, size_x, offset_y, size_y] or [] or None.
        :return: Signal ROI as a list.
        """
        rest_endpoint = "/roi_signal"

        server_response = requests.post(self.api_address_format % rest_endpoint, json=roi).json()
        return validate_response(server_response)["roi_signal"]

    def get_roi_background(self):
        """
        Get the ROI for the background.
        :return: Background ROI as a list.
        """
        rest_endpoint = "/roi_background"

        server_response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(server_response)["roi_background"]

    def set_roi_background(self, roi):
        """
        Set the ROI for the background.
        :param roi: List of 4 elements: [offset_x, size_x, offset_y, size_y] or [] or None.
        :return: Background ROI as a list.
        """
        rest_endpoint = "/roi_background"

        server_response = requests.post(self.api_address_format % rest_endpoint, json=roi).json()
        return validate_response(server_response)["roi_background"]
