from .endpoint.http_endpoint import EndpointConfig
from .endpoint.kv_endpoint import KVEndpoint
from .endpoint.service_endpoint import ServiceEndpoint


class ConsulClient(object):
    """Client to use the API.
    """

    def __init__(self, config=EndpointConfig()):
        self.config = config
        self._service = ServiceEndpoint(endpoint_config=config, url_parts=["agent"])
        self._kv = KVEndpoint(endpoint_config=config, url_parts=["kv"])

    @property
    def service(self) -> ServiceEndpoint:
        """Get the agent service instance.
        """
        return self._service

    @property
    def kv(self) -> KVEndpoint:
        """Get the key value service instance.
        """
        return self._kv
