import logging
from typing import List
from urllib.parse import urlencode

from .common import Response
from .decoder import Decoder
from .http_client import HttpRequest, HttpResponse

LOGGER = logging.getLogger(__name__)


class EndpointConfig:
    """Config to connect to Consul.
    """

    def __init__(self,
                 host="127.0.0.1",
                 port=8500,
                 version='v1',
                 datacenter=None,
                 token=None,
                 scheme='http',
                 transport=None):
        self.host = host
        self.port = port
        self.version = version
        self.datacenter = datacenter
        self.token = token
        self.scheme = scheme
        if transport is None:
            transport = HttpRequest(token=token)
        self.transport = transport

    def compose_base_uri(self) -> str:
        """Return the base URI for API requests.
        """

        if self.port:
            return '{0}://{1}:{2}/{3}'.format(self.scheme, self.host, self.port, self.version)
        return '{0}://{1}/{2}'.format(self.scheme, self.host, self.version)


class HttpEndpoint(object):
    """Base class for API endpoints"""

    def __init__(self, endpoint_config: EndpointConfig, url_parts: List[str]):
        """Create a new instance of the Endpoint class
        """
        self._endpoint_config = endpoint_config
        self._base_uri = endpoint_config.compose_base_uri()
        if url_parts is not None and len(url_parts) > 0:
            self._base_uri = '{0}/{1}'.format(self._base_uri, '/'.join(url_parts))

    def build_uri(self, params, query_params=None):
        """Build the request URI
        """
        if not query_params:
            query_params = dict()
        if self._endpoint_config.datacenter:
            query_params['dc'] = self._endpoint_config.datacenter
        if self._endpoint_config.token:
            query_params['token'] = self._endpoint_config.token
        path = '/'.join(params)
        if query_params:
            return '{0}/{1}?{2}'.format(self._base_uri, path,
                                        urlencode(query_params))
        return '{0}/{1}'.format(self._base_uri, path)

    def get_response(self, url_parts=None, query=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        uri = self.build_uri(url_parts, query)
        return self._endpoint_config.transport.get(uri)

    def post_response(self, url_parts, query=None, payload=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        return self._endpoint_config.transport.post(self.build_uri(url_parts, query), payload)

    def put_response(self, url_parts, query=None, payload=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        return self._endpoint_config.transport.put(self.build_uri(url_parts, query), payload)

    def delete_response(self, url_parts, query=None) -> HttpResponse:
        if url_parts is None:
            url_parts = []

        return self._endpoint_config.transport.delete(self.build_uri(url_parts, query))

    @staticmethod
    def decode_response(response: HttpResponse, decoder: Decoder):
        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        result = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, result
