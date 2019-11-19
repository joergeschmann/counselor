import base64
import json
import logging

import requests

LOGGER = logging.getLogger(__name__)

CONTENT_FORM = 'application/x-www-form-urlencoded; charset=utf-8'
CONTENT_JSON = 'application/json; charset=utf-8'

HEADER_JSON = {
    'Content-Type': CONTENT_JSON
}


class Response(object):
    """Used to process and wrap the responses from Consul.
    """
    status_code = None
    payload = None
    headers = None

    def __init__(self, status_code, body, headers):
        self.status_code = status_code
        self.payload = self._unmarshal(body)
        self.headers = headers

    @staticmethod
    def from_http_response(response: requests.Response) -> 'Response':
        return Response(response.status_code, response.content, response.headers)

    def is_successful(self) -> bool:
        return 200 <= self.status_code < 400

    def as_string(self) -> str:
        return "{}: {}".format(self.status_code, self.payload)

    def _unmarshal(self, body):
        if body is None:
            return None

        if self.status_code == 200:
            if body is None:
                return None
            elif len(body) == 0:
                return ''

            try:
                value = json.loads(body, encoding='utf-8')
            except Exception as exc:
                LOGGER.warning("Could not unmarshal json: {}".format(exc))
                return body

            if value is None:
                return None
            if isinstance(value, bool):
                return value
            if 'error' not in value:
                for row in value:
                    if 'Value' in row:
                        try:
                            row['Value'] = base64.b64decode(row['Value'])
                            if isinstance(row['Value'], bytes):
                                try:
                                    row['Value'] = row['Value'].decode('utf-8')
                                except UnicodeDecodeError:
                                    pass
                        except TypeError:
                            pass

            if isinstance(value, list) and len(value) == 1:
                return value[0]
            return value

        return body


class Request(object):
    """The Request adapter class"""

    def __init__(self, timeout=None):
        self.session = requests.Session()
        self.timeout = timeout

    def get(self, uri) -> Response:
        """Send a HTTP get request.
        """
        LOGGER.debug("GET %s", uri)
        http_response = self.session.get(uri, timeout=self.timeout)
        return Response.from_http_response(http_response)

    def post(self, uri, data=None, headers=None) -> Response:
        """Send a HTTP post request.
        """
        LOGGER.debug("POST %s with %r", uri, data)
        if headers is None:
            headers = HEADER_JSON
        http_response = self.session.post(uri, data=None, headers=headers, timeout=self.timeout, json=data)
        return Response.from_http_response(http_response)

    def put(self, uri, data=None, headers=None) -> Response:
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

        return Response.from_http_response(http_response)

    def delete(self, uri) -> Response:
        """Send a HTTP delete request.
        """
        LOGGER.debug("DELETE %s", uri)
        http_response = self.session.delete(uri, timeout=self.timeout)
        return Response.from_http_response(http_response)
