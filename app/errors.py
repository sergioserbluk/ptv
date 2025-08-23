from flask import jsonify


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        response = jsonify({"status": "error", "message": err.message})
        response.status_code = err.status_code
        return response

    @app.errorhandler(404)
    def handle_404(err):
        response = jsonify({"status": "error", "message": "Not found"})
        response.status_code = 404
        return response

    @app.errorhandler(Exception)
    def handle_exception(err):
        response = jsonify({"status": "error", "message": str(err)})
        response.status_code = 500
        return response
