import logging

from .common import Response
from .decoder import JsonDecoder, ConsulKVDecoder
from .entity import ConsulKeyValue
from .http_client import HttpResponse
from .http_endpoint import HttpEndpoint

LOGGER = logging.getLogger(__name__)


class KV(HttpEndpoint):
    """Key value store interface to consul. This class is meant to store dicts as values.

        TODO: use StatusResponse as returned value
    """

    def get_raw(self, item) -> (Response, dict):
        query_params = {'raw': True}
        response = self._get(item=item, query_params=query_params)

        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = JsonDecoder()
        result = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, result

    def get(self, item) -> (Response, ConsulKeyValue):
        """Get a value.
        Raw means without the Consul metadata like CreateIndex and ModifyIndex.
        """

        response = self._get(item=item)

        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = ConsulKVDecoder()
        consul_kv = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, consul_kv

    def _get(self, item: str, query_params=None) -> HttpResponse:
        if query_params is None:
            query_params = {}

        item = item.lstrip('/')
        return self.get_response(url_parts=[item], query=query_params)

    def set(self, item: str, value, flags=None) -> Response:
        """Set a value.
        """

        item = item.rstrip('/')
        query_params = {}
        if flags is not None:
            query_params['flags'] = flags

        response = self.put_response(url_parts=[item], query=query_params, payload=value)
        return Response.create_from_http_response(response)

    def delete(self, item, recurse=False) -> Response:
        """Remove an item.
        """

        query_params = {'recurse': True} if recurse else {}
        response = self.delete_response(url_parts=[item], query=query_params)
        return Response.create_from_http_response(response)

    def acquire_lock(self, item, session) -> Response:
        """Set a lock.
        """

        response = self.put_response(url_parts=[item], query=None, payload={'acquire': session})
        return Response.create_from_http_response(response)

    def release_lock(self, item, session) -> Response:
        """Release a lock.
        """
        response = self.put_response(url_parts=[item], query=None, payload={'release': session})
        return Response.create_from_http_response(response)
