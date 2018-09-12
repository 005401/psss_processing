import json
import logging

import bottle
from bottle import request, response

from psss_processing import config
from psss_processing.utils import get_png_from_image

_logger = logging.getLogger(__name__)


def register_rest_interface(app, instance_manager):

    api_root_address = config.API_PREFIX

    @app.post(api_root_address + "/start")
    def start():

        instance_manager.start()

        return {"state": "ok",
                "status": instance_manager.get_status()}

    @app.post(api_root_address + "/stop")
    def stop():

        instance_manager.stop()

        return {"state": "ok",
                "status": instance_manager.get_status()}

    @app.get(api_root_address + "/status")
    def get_status():
        return {"state": "ok",
                "status": instance_manager.get_status()}

    @app.get(api_root_address + "/roi")
    def get_roi():

        return {"state": "ok",
                "status": instance_manager.get_status(),
                "roi": instance_manager.get_roi()}

    @app.post(api_root_address + "/roi")
    def set_roi():
        roi = request.json
        instance_manager.set_roi(roi)

        return {"state": "ok",
                "status": instance_manager.get_status(),
                "roi": instance_manager.get_roi()}

    @app.get(api_root_address + "/parameters")
    def get_parameters():
        return {"state": "ok",
                "status": instance_manager.get_status(),
                "parameters": instance_manager.get_parameters()}

    @app.post(api_root_address + "/parameters")
    def set_parameters():
        parameters = request.json
        instance_manager.set_parameters(parameters)

        return {"state": "ok",
                "status": instance_manager.get_status(),
                "parameters": instance_manager.get_parameters()}

    @app.get(api_root_address + "/statistics")
    def get_statistics():

        return {"state": "ok",
                "status": instance_manager.get_status(),
                "statistics": instance_manager.get_statistics()}

    @app.get(api_root_address + '/image')
    def get_image():
        # Retrieve the last processed image.
        image_raw_bytes = instance_manager.get_last_processed_image()

        if image_raw_bytes is not None:
            image = get_png_from_image(image_raw_bytes)
            response.set_header('Content-type', 'image/png')
            return image

        return "No image was processed yet. Please process at least 1 image before calling this method."

    @app.error(405)
    def method_not_allowed(res):

        if request.method == 'OPTIONS':
            new_res = bottle.HTTPResponse()
            new_res.set_header('Access-Control-Allow-Origin', '*')
            new_res.set_header('Access-Control-Allow-Methods', 'PUT, GET, POST, DELETE, OPTIONS')
            new_res.set_header('Access-Control-Allow-Headers', 'Origin, Accept, Content-Type')
            return new_res

        res.headers['Allow'] += ', OPTIONS'
        return request.app.default_error_handler(res)

    @app.hook('after_request')
    def enable_cors():

        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = \
            'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

    @app.error(500)
    def error_handler_500(error):

        response.content_type = 'application/json'
        response.status = 200

        return json.dumps({"state": "error",
                           "status": str(error.exception)})
