from typing import List

from .check_endpoint import CheckEndpoint
from .common import Response
from .decoder import ServiceDefinitionListDecoder, JsonDecoder, Decoder
from .entity import ServiceDefinition
from .http_endpoint import HttpEndpoint, EndpointConfig
from .service_endpoint import ServiceEndpoint


class AgentEndpoint(HttpEndpoint):
    """The Consul agent registers, deregisters and checks services.
    """

    def __init__(self, endpoint_config: EndpointConfig, url_parts: List[str]):
        """Create a new instance of the Agent.
        """

        if url_parts is None:
            url_parts = ["agent"]

        super(AgentEndpoint, self).__init__(endpoint_config, url_parts)

        self.check = CheckEndpoint(endpoint_config, url_parts + ["check"])
        self.service = ServiceEndpoint(endpoint_config, url_parts + ["service"])

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
