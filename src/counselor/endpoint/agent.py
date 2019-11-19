from typing import List

from .check import Check
from .encoding import ServiceDefinitionListDecoder, StatusResponse, ServiceDefinition
from .endpoint import Endpoint
from .service import Service


class Agent(Endpoint):
    """The Consul agent registers, deregisters and checks services.
    """

    def __init__(self, uri, transport, datacenter=None, token=None):
        """Create a new instance of the Agent.
        """

        super(Agent, self).__init__(uri, transport, datacenter, token)
        self.check = Check(self._base_uri, transport, datacenter, token)
        self.service = Service(self._base_uri, transport, datacenter, token)

    def checks(self):
        """Return all the checks that are registered with the local agent.
        For now, we use our own watcher, to have a simple class to reconfigure a service when a change occurs.
        """

        return self._get_response(url_parts=['checks'], response_parser=None)

    def force_leave(self, node):
        """Leave a cluster.
        """

        return self._get_response(url_parts=['force-leave', node], response_parser=None)

    def join(self, address, wan=False):
        """Join a cluster.
        """

        query_params = {'wan': 1} if wan else None
        return self._get_response(url_parts=['join', address], query=query_params, response_parser=None)

    def members(self):
        """Return the members the agent sees in the cluster gossip pool.
        """

        return self._get_response(url_parts=['members'], response_parser=None)

    def services(self, query: List[tuple] = None) -> (StatusResponse, List[ServiceDefinition]):
        """Return all the services that are registered with the local agent.
        """

        return self._get_response(url_parts=['services'], query=query, response_parser=ServiceDefinitionListDecoder())
