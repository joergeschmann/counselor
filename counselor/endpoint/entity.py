import json
from typing import List


class ServiceDefinition:
    """This class holds an internal representation of the Consul structure for a service.
    """

    def __init__(self, key: str, address=None, port=0, tags=None, meta=None, content_hash=None):
        self.key = key
        self.address = address
        self.port = port

        self.tags: List[str] = []
        self.set_tags(tags)

        self.meta: dict = {}
        self.set_meta(meta)

        self.content_hash = content_hash
        self.check = None
        self.interval = None
        self.ttl = None
        self.http_check = None

    @staticmethod
    def new_simple_service_definition(key: str, tags=None, meta=None):
        return ServiceDefinition(key=key, tags=tags, meta=meta)

    def set_tags(self, tags: List[str] = None):
        if tags is None:
            tags = []

        self.tags = tags

    def set_meta(self, meta: dict = None):
        if meta is None:
            meta = {}

        self.meta = meta

    def validate(self):
        if self.port and not isinstance(self.port, int):
            raise ValueError('Port must be an integer')
        elif self.tags and not isinstance(self.tags, list):
            raise ValueError('Tags must be a list of strings')
        elif (self.check or self.http_check) and self.ttl:
            raise ValueError('Can not specify both a check and ttl')

        if (self.check or self.http_check) and not self.interval:
            raise ValueError('An interval is required for check scripts and http checks.')

    def as_json(self) -> str:
        return json.dumps(self.__dict__)


class ConsulKeyValue:
    """Key value entry in Consul. The value might be base64 encoded json.
    [{"LockIndex":0,"Key":"test","Flags":0,"Value":"ewogICJmb28iOiAzLjE0MTUKfQ==","CreateIndex":5331,"ModifyIndex":5331}]
    """

    def __init__(self, key: str = "", value: dict = None, flags: List[str] = None, lock_index=0, create_index=0,
                 modify_index=0):
        if value is None:
            value = {}
        if flags is None:
            flags = []

        self.key = key
        self.value = value
        self.flags = flags
        self.lock_index = lock_index
        self.create_index = create_index
        self.modify_index = modify_index
