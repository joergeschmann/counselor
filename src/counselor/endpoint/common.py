from .decoder import Decoder
from .http_client import HttpResponse


class Response:
    """StatusResponse is used as a standard response to indicate whether a request to Consul was successful or not.
    """

    def __init__(self, successful=True, kind="", message="", exception: Exception = None):
        self.successful = successful
        self.kind = kind
        self.message = message
        self.exception = exception

    @staticmethod
    def create_successful_result():
        return Response()

    @staticmethod
    def create_error_result(kind="", message=""):
        return Response(successful=False, kind=kind, message=message)

    @staticmethod
    def create_error_result_with_exception_only(exception: Exception):
        return Response(successful=False, exception=exception)

    @staticmethod
    def create_error_result_with_message_only(message=""):
        return Response.create_error_result(message=message)

    @staticmethod
    def create_from_http_response(response: HttpResponse):
        if response.is_successful():
            return Response(kind=response.status_code)
        else:
            return Response.create_error_result(kind=response.status_code, message=response.payload)

    def update_by_decode_result(self, decoder: Decoder):
        if not decoder.successful:
            self.kind = "DecodeError"
            self.message = decoder.error_message
            self.exception = decoder.exception

    def as_string(self) -> str:
        return "successful: {} \nkind: {} \nmessage: {} \nexception: {}".format(self.successful, self.kind,
                                                                                self.message,
                                                                                self.exception)

    class ErrorTypes:
        NotDefined = "NotDefined"
