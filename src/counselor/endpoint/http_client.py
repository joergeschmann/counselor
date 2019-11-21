import logging

from requests import Response, Session

LOGGER = logging.getLogger(__name__)

CONTENT_FORM = 'application/x-www-form-urlencoded; charset=utf-8'
CONTENT_JSON = 'application/json; charset=utf-8'

HEADER_JSON = {
    'Content-Type': CONTENT_JSON
}


class HttpResponse(object):
    """Used to process and wrap the responses from Consul.
    """
    status_code = None
    payload = None
    headers = None

    def __init__(self, status_code, body, headers):
        self.status_code = status_code
        self.payload = body
        self.headers = headers

    @staticmethod
    def from_http_response(response: Response) -> 'HttpResponse':
        return HttpResponse(response.status_code, response.content, response.headers)

    def is_successful(self) -> bool:
        return 200 <= self.status_code < 400

    def as_string(self) -> str:
        return "{}: {}".format(self.status_code, self.payload)


class HttpRequest(object):
    """The Request adapter class"""

    def __init__(self, timeout=None):
        self.session = Session()
        self.timeout = timeout

    def get(self, uri) -> HttpResponse:
        """Send a HTTP get request.
        """
        LOGGER.debug("GET %s", uri)
        http_response = self.session.get(uri, timeout=self.timeout)
        return HttpResponse.from_http_response(http_response)

    def post(self, uri, data=None, headers=None) -> HttpResponse:
        """Send a HTTP post request.
        """
        LOGGER.debug("POST %s with %r", uri, data)
        if headers is None:
            headers = HEADER_JSON

        http_response = self.session.post(uri, data=None, headers=headers, timeout=self.timeout, json=data)
        return HttpResponse.from_http_response(http_response)

    def put(self, uri, data=None, headers=None) -> HttpResponse:
        """Send a HTTP put request
        """
        LOGGER.debug("PUT %s with %r", uri, data)
        if headers is None:
            headers = HEADER_JSON

        data_type = type(data)
        if data_type == str:
            http_response = self.session.put(uri, data=data, headers=headers, timeout=self.timeout, json=None)
        else:
            http_response = self.session.put(uri, data=None, headers=headers, timeout=self.timeout, json=data)

        return HttpResponse.from_http_response(http_response)

    def delete(self, uri) -> HttpResponse:
        """Send a HTTP delete request.
        """
        LOGGER.debug("DELETE %s", uri)
        http_response = self.session.delete(uri, timeout=self.timeout)
        return HttpResponse.from_http_response(http_response)
