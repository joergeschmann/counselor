import logging
from urllib.parse import urlencode

from .encoding import Decoder
from .http import Request

LOGGER = logging.getLogger(__name__)


class Endpoint(object):
    """Base class for API endpoints"""

    def __init__(self, uri, transport=Request(), datacenter=None, token=None):
        """Create a new instance of the Endpoint class
        """
        self._transport = transport
        self._base_uri = '{0}/{1}'.format(uri, self.__class__.__name__.lower())
        self._dc = datacenter
        self._token = token

    def _build_uri(self, params, query_params=None):
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

    def _get_response(self, url_parts=None, query=None, response_parser: Decoder = None):
        if url_parts is None:
            url_parts = []

        uri = self._build_uri(url_parts, query)
        response = self._transport.get(uri)

        if response_parser is None:
            return response

        return response_parser.decode(response)

    def _post_response(self, url_parts, query=None, payload=None, response_parser: Decoder = None):
        if url_parts is None:
            url_parts = []

        response = self._transport.post(self._build_uri(url_parts, query), payload)

        if response_parser is None:
            return response

        return response_parser.decode(response)

    def _put_response(self, url_parts, query=None, payload=None, response_parser: Decoder = None):
        if url_parts is None:
            url_parts = []

        response = self._transport.put(self._build_uri(url_parts, query), payload)

        if response_parser is None:
            return response

        return response_parser.decode(response)

    def _delete_response(self, url_parts, query=None, response_parser: Decoder = None):
        if url_parts is None:
            url_parts = []

        response = self._transport.delete(self._build_uri(url_parts, query))

        if response_parser is None:
            return response

        return response_parser.decode(response)
