import logging
from typing import List

from .common import Response
from .decoder import JsonDecoder, ConsulKVDecoder, ConsulKVListDecoder
from .entity import ConsulKeyValue
from .http_client import HttpResponse
from .http_endpoint import HttpEndpoint, EndpointConfig

LOGGER = logging.getLogger(__name__)


class KVPath:
    def __init__(self, project: str, domain: str, service: str, detail: str = "config", env: str = "dev"):
        self.project = project
        self.domain = domain
        self.service = service
        self.detail = detail
        self.env = env

    @staticmethod
    def parse_from_path(path: str) -> 'KVPath':
        splitted_path = path.split('/')
        if len(splitted_path) != 5:
            raise ValueError("Path should have 5 parts")

        return KVPath(project=splitted_path[0],
                      domain=splitted_path[2],
                      service=splitted_path[3],
                      detail=splitted_path[4],
                      env=splitted_path[1])

    def compose_path(self) -> str:
        return "{}/{}/{}/{}/{}".format(self.project, self.env, self.domain, self.service, self.detail)


class KVEndpoint(HttpEndpoint):
    """Key value store interface to consul. This class is meant to store dicts as values.

        TODO: use StatusResponse as returned value
    """

    def __init__(self, endpoint_config: EndpointConfig, url_parts: List[str]):
        if url_parts is None:
            url_parts = ["kv"]
        super().__init__(endpoint_config, url_parts)

    def get_raw(self, path) -> (Response, dict):
        """Return the raw config as dict, without the Consul specific fields."""
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

    def get_recursive(self, path) -> (Response, List[ConsulKeyValue]):
        """Return an array of all the entires from the path downwards"""
        query_params = {'recurse': True}

        response = self._get(path=path, query_params=query_params)

        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = ConsulKVListDecoder()
        result_list = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder)

        return endpoint_response, result_list

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

    def merge(self, path: str, updates: dict) -> Response:
        """Try to fetch an existing config. If successful, overwrite the values with the updates.
        Otherwise assume that there is no config yet and try to store it."""

        response, config = self.get_raw(path)
        if not response.successful:
            return self.set(path, updates)

        if not isinstance(config, dict):
            return Response.create_error_result_with_message_only("Current config is not a dict")

        for key in updates.keys():
            config[key] = updates[key]

        return self.set(path, config)

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
