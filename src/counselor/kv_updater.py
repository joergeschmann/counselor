from .client import ConsulClient
from .endpoint.common import Response


class KVUpdater:
    """Helper class to conveniently update configs in Consul KV store."""

    def __init__(self, kv_path: str, consul_client: ConsulClient):
        self.kv_path = kv_path
        self.consul_client = consul_client

    def update(self, config: dict) -> Response:
        return self.consul_client.kv.set(self.kv_path, config)

    def merge(self, config: dict):
        return self.consul_client.kv.merge(self.kv_path, config)
