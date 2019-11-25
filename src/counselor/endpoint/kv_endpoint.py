import logging
from typing import List

from .common import Response
from .decoder import JsonDecoder, ConsulKVDecoder
from .entity import ConsulKeyValue
from .http_client import HttpResponse
from .http_endpoint import HttpEndpoint, EndpointConfig

LOGGER = logging.getLogger(__name__)


class KVEndpoint(HttpEndpoint):
    """Key value store interface to consul. This class is meant to store dicts as values.

        TODO: use StatusResponse as returned value
    """

    def __init__(self, endpoint_config: EndpointConfig, url_parts: List[str]):
        if url_parts is None:
            url_parts = ["kv"]
        super().__init__(endpoint_config, url_parts)

    def get_raw(self, path) -> (Response, dict):
        query_params = {'raw': True}
        response = self._get(path=path, query_params=query_params)

        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = JsonDecoder()
        result = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, result

    def get(self, path) -> (Response, ConsulKeyValue):
        """Get a value.
        Raw means without the Consul metadata like CreateIndex and ModifyIndex.
        """

        response = self._get(path=path)

        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = ConsulKVDecoder()
        consul_kv = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, consul_kv

    def _get(self, path: str, query_params=None) -> HttpResponse:
        if path is None or path == "":
            return HttpResponse(status_code=500, body="Path can not be empty", headers=None)

        if query_params is None:
            query_params = {}

        path = path.lstrip('/')
        return self.get_response(url_parts=[path], query=query_params)

    def set(self, path: str, value, flags=None) -> Response:
        """Set a value.
        """

        path = path.rstrip('/')
        query_params = {}
        if flags is not None:
            query_params['flags'] = flags

        response = self.put_response(url_parts=[path], query=query_params, payload=value)
        return Response.create_from_http_response(response)

    def delete(self, path, recurse=False) -> Response:
        """Remove an item.
        """

        query_params = {'recurse': True} if recurse else {}
        response = self.delete_response(url_parts=[path], query=query_params)
        return Response.create_from_http_response(response)

    def acquire_lock(self, path, session) -> Response:
        """Set a lock.
        """

        response = self.put_response(url_parts=[path], query=None, payload={'acquire': session})
        return Response.create_from_http_response(response)

    def release_lock(self, path, session) -> Response:
        """Release a lock.
        """
        response = self.put_response(url_parts=[path], query=None, payload={'release': session})
        return Response.create_from_http_response(response)
