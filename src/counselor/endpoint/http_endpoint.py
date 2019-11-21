import logging
from urllib.parse import urlencode

from .common import Response
from .decoder import Decoder
from .http_client import HttpRequest, HttpResponse

LOGGER = logging.getLogger(__name__)


class HttpEndpoint(object):
    """Base class for API endpoints"""

    def __init__(self, uri, request=HttpRequest(), datacenter=None, token=None):
        """Create a new instance of the Endpoint class
        """
        self._request = request
        self._base_uri = '{0}/{1}'.format(uri, self.__class__.__name__.lower())
        self._dc = datacenter
        self._token = token

    def build_uri(self, params, query_params=None):
        """Build the request URI
        """
        if not query_params:
            query_params = dict()
        if self._dc:
            query_params['dc'] = self._dc
        if self._token:
            query_params['token'] = self._token
        path = '/'.join(params)
        if query_params:
            return '{0}/{1}?{2}'.format(self._base_uri, path,
                                        urlencode(query_params))
        return '{0}/{1}'.format(self._base_uri, path)

    def get_response(self, url_parts=None, query=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        uri = self.build_uri(url_parts, query)
        return self._request.get(uri)

    def post_response(self, url_parts, query=None, payload=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        return self._request.post(self.build_uri(url_parts, query), payload)

    def put_response(self, url_parts, query=None, payload=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        return self._request.put(self.build_uri(url_parts, query), payload)

    def delete_response(self, url_parts, query=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        return self._request.delete(self.build_uri(url_parts, query))

    @staticmethod
    def decode_response(response: HttpResponse, decoder: Decoder):
        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        result = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, result
