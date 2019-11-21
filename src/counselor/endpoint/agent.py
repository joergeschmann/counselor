from typing import List

from .check import Check
from .common import Response
from .decoder import ServiceDefinitionListDecoder, JsonDecoder, Decoder
from .entity import ServiceDefinition
from .http_endpoint import HttpEndpoint
from .service import Service


class Agent(HttpEndpoint):
    """The Consul agent registers, deregisters and checks services.
    """

    def __init__(self, uri, request, datacenter=None, token=None):
        """Create a new instance of the Agent.
        """

        super(Agent, self).__init__(uri, request, datacenter, token)
        self.check = Check(self._base_uri, request, datacenter, token)
        self.service = Service(self._base_uri, request, datacenter, token)

    def checks(self) -> (Response, List[str]):
        """Return all the checks that are registered with the local agent.
        For now, we use our own watcher, to have a simple class to reconfigure a service when a change occurs.
        """

        response = self.get_response(url_parts=['checks'])
        return HttpEndpoint.decode_response(response, JsonDecoder())

    def force_leave(self, node) -> Response:
        """Leave a cluster.
        """

        response = self.get_response(url_parts=['force-leave', node])
        return HttpEndpoint.decode_response(response, Decoder())

    def join(self, address, wan=False) -> Response:
        """Join a cluster.
        """

        query_params = {'wan': 1} if wan else None
        response = self.get_response(url_parts=['join', address], query=query_params)
        return HttpEndpoint.decode_response(response, Decoder())

    def members(self) -> (Response, List[str]):
        """Return the members the agent sees in the cluster gossip pool.
        """

        response = self.get_response(url_parts=['members'])
        return HttpEndpoint.decode_response(response, JsonDecoder())

    def services(self, query: List[tuple] = None) -> (Response, List[ServiceDefinition]):
        """Return all the services that are registered with the local agent.
        """

        response = self.get_response(url_parts=['services'], query=query)
        return HttpEndpoint.decode_response(response, ServiceDefinitionListDecoder())
