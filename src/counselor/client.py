from .endpoint.agent_endpoint import AgentEndpoint
from .endpoint.http_endpoint import EndpointConfig
from .endpoint.kv_endpoint import KVEndpoint


class Consul(object):
    """Client to use the API.
    """

    def __init__(self, config=EndpointConfig()):
        self.config = config
        self._agent = AgentEndpoint(endpoint_config=config, url_parts=["agent"])
        self._kv = KVEndpoint(endpoint_config=config, url_parts=["kv"])

    @property
    def agent(self) -> AgentEndpoint:
        """Get the agent service instance.
        """
        return self._agent

    @property
    def kv(self) -> KVEndpoint:
        """Get the key value service instance.
        """
        return self._kv
