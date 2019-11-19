from .endpoint.agent import Agent
from .endpoint.http import Request
from .endpoint.keyvalue import KV


class ConsulConfig:
    """Config to connect to Consul.
    """

    def __init__(self,
                 host="127.0.0.1",
                 port=8500,
                 version='v1',
                 datacenter=None,
                 token=None,
                 scheme='http',
                 transport=Request()):
        self.host = host
        self.port = port
        self.version = version
        self.datacenter = datacenter
        self.token = token
        self.scheme = scheme
        self.transport = transport

    def compose_base_uri(self) -> str:
        """Return the base URI for API requests.
        """

        if self.port:
            return '{0}://{1}:{2}/{3}'.format(self.scheme, self.host, self.port, self.version)
        return '{0}://{1}/{2}'.format(self.scheme, self.host, self.version)


class Consul(object):
    """Client to use the API.
    """

    def __init__(self, config=ConsulConfig()):
        self.config = config
        base_uri = config.compose_base_uri()
        self._agent = Agent(base_uri, config.transport, config.datacenter, config.token)
        self._kv = KV(base_uri, config.transport, config.datacenter, config.token)

    @property
    def agent(self) -> Agent:
        """Get the agent service instance.
        """
        return self._agent

    @property
    def kv(self) -> KV:
        """Get the key value service instance.
        """
        return self._kv
