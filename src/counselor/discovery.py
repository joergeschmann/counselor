import logging
from datetime import timedelta
from threading import Event
from typing import List

from .client import ConsulClient
from .endpoint.common import Response
from .endpoint.entity import ServiceDefinition
from .endpoint.http_endpoint import EndpointConfig
from .endpoint.kv_endpoint import KVPath
from .filter import KeyValuePair, Filter, Operators
from .kv_updater import KVUpdater
from .kv_watcher import KVWatcherTask, ConfigUpdateListener
from .trigger import Trigger

LOGGER = logging.getLogger(__name__)


class ReconfigurableService:
    """Base class to hold all the information about a service."""

    @staticmethod
    def create_with_service_definition(service_definition: ServiceDefinition, config_path: KVPath,
                                       current_config: dict) -> 'ReconfigurableService':
        return ReconfigurableService(service_definition.key, config_path=config_path, current_config=current_config,
                                     tags=service_definition.tags, meta=service_definition.meta)

    def __init__(self, service_key: str, config_path: KVPath, current_config: dict = None, tags: List[str] = None,
                 meta: dict = None):
        self.service_key = service_key
        self._config_path = config_path
        self.current_config = current_config
        self.tags = tags
        self.meta = meta

    def compose_config_path(self) -> str:
        """Return the config path where the config is stored, for example via KVConfigPath.compose_path()
        """
        return self._config_path.compose_path()

    def to_service_definition(self) -> ServiceDefinition:
        """Create an instance of ServiceDefinition"""
        return ServiceDefinition(key=self.service_key, tags=self.tags, meta=self.meta)


class ServiceDiscovery:
    """Facade to interact with Consul. The use case is that you have a service you want to register in Consul.
    The service definition is stored to the service module, whereas the configuration for the service is persisted in
    the Consul KV store. After your service is registered, you can start a config watcher, that periodically
    fetches the config from Consul KV store. If there is a change in the configuration, the service is notified to reconfigure itself.
    """

    def __init__(self, consul_client: ConsulClient):
        self._consul_client = consul_client
        self._trigger = Trigger()

    @staticmethod
    def new_service_discovery_with_defaults() -> 'ServiceDiscovery':
        return ServiceDiscovery.new_service_discovery_with_consul_config(EndpointConfig())

    @staticmethod
    def new_service_discovery_with_consul_config(config: EndpointConfig) -> 'ServiceDiscovery':
        return ServiceDiscovery.new_service_discovery_with_consul_client(ConsulClient(config))

    @staticmethod
    def new_service_discovery_with_consul_client(client: ConsulClient) -> 'ServiceDiscovery':
        return ServiceDiscovery(client)

    @staticmethod
    def new_service_discovery_with_config_details(consul_ip: str = "127.0.0.1",
                                                  consul_port: int = 8500) -> 'ServiceDiscovery':
        return ServiceDiscovery.new_service_discovery_with_consul_config(
            EndpointConfig(host=consul_ip, port=consul_port))

    def fetch_config_or_default(self, path: str, default: dict, merge: False):
        """Try to fetch the config from Consul. If a config is available, merge it if needed and return it.
        If there is no config available return the default."""
        response, config = self.fetch_config_by_path(path)
        if config:
            if not merge:
                return config

            for key in config.keys():
                default[key] = config[key]

            return config

        return default

    def fetch_config_by_path(self, path: str) -> (Response, dict):
        return self._consul_client.kv.get_raw(path)

    def fetch_config_recursively(self, path: str) -> (Response, List[dict]):
        result_list = []

        response, kv_list = self._consul_client.kv.get_recursive(path)
        if response.successful and kv_list is not None:
            for e in kv_list:
                result_list.append(e.value)

        return response, result_list

    def store_config(self, path: str, config: dict) -> Response:
        """Store the config in Consul.
        """
        return self._consul_client.kv.set(path, config)

    def update_config(self, path: str, config: dict) -> Response:
        """Update the config in Consul.
        """
        return self._consul_client.kv.set(path, config)

    def merge_config(self, path: str, updates: dict) -> Response:
        """Merge updates with existing config."""

        return self._consul_client.kv.merge(path, updates)

    def delete_config(self, path: str, recurse=False):
        return self._consul_client.kv.delete(path, recurse=recurse)

    def register_service(self, service_definition: ServiceDefinition) -> Response:
        """Register a ServiceDefinition in Consul.
        """

        LOGGER.info("Registering service definition {}".format(service_definition.key))

        return self._update_service_definition(service_definition)

    def get_service_details(self, service_key) -> (Response, ServiceDefinition):
        return self._consul_client.service.get_details(service_key)

    def update_service(self, service_definition: ServiceDefinition) -> Response:
        """Update the ServiceDefinition in Consul.
        Update is the same as a registration.
        """
        LOGGER.info("Updating service definition {}".format(service_definition.key))

        return self._update_service_definition(service_definition)

    def register_service_and_store_config(self, service: ReconfigurableService) -> Response:
        register_response = self.register_service(service.to_service_definition())
        if not register_response.successful:
            return register_response

        return self.store_config(service.compose_config_path(), service.current_config)

    def _update_service_definition(self, service_definition: ServiceDefinition) -> Response:
        return self._consul_client.service.register(service_definition)

    def deregister_service(self, service_key: str) -> Response:
        """Delete the ServiceDefinition in Consul. Also stops the watcher if still active.
        """

        if service_key is None or service_key == "":
            return Response.create_successful_result()

        LOGGER.info("Deregistering service {}".format(service_key))

        try:
            if self._trigger is not None and self._trigger.running:
                LOGGER.info("Stopping config watch first")
                self.stop_config_watch()

            return self._consul_client.service.deregister(service_key)
        except Exception as exc:
            return Response.create_error_result_with_message_only("{}".format(exc))

    def search_for_services(self, tags: List[str] = None, meta: List[KeyValuePair] = None) -> (
            Response, List[ServiceDefinition]):
        """Search for active ServiceDefinitions.
        """

        if tags is None:
            tags = []

        if meta is None:
            meta = {}

        filter_tuples = []

        for e in tags:
            filter_expression = Filter.new_tag_filter(Operators.OPERATOR_IN, e).as_expression()
            query_tuple = ('filter', filter_expression)
            filter_tuples.append(query_tuple)

        for e in meta:
            filter_expression = Filter.new_meta_filter(e.key, Operators.OPERATOR_EQUALITY, e.value).as_expression()
            query_tuple = ('filter', filter_expression)
            filter_tuples.append(query_tuple)

        return self._consul_client.service.search(filter_tuples)

    def add_multiple_config_watches(self, listeners: List[ConfigUpdateListener], check_interval: timedelta,
                                    stop_event=Event()):
        """Add a list of config watchers
        """

        if listeners is None or len(listeners) == 0:
            return

        for listener in listeners:
            if listener is None:
                continue

            self.add_config_watch(listener, check_interval=check_interval, stop_event=stop_event)

    def add_config_watch(self, listener: ConfigUpdateListener, check_interval: timedelta,
                         stop_event=Event()):
        """Create a watcher that periodically checks for config changes.
        """

        if listener is None:
            return

        LOGGER.info("Adding config watch for {}".format(listener.get_path()))
        watcher_task = KVWatcherTask(listener, self._consul_client, check_interval, stop_event)
        self._trigger.add_task(watcher_task)

    def clear_watchers(self):
        """Remove all the watchers"""
        self._trigger.clear()

    def start_config_watch(self) -> Response:
        """Start the config watcher tasks
        """

        LOGGER.info("Starting config watches")

        try:
            self._trigger.run_nonblocking()
        except Exception as exc:
            return Response.create_error_result_with_message_only("{}".format(exc))

        return Response.create_successful_result()

    def stop_config_watch(self):
        """Stop the watcher.
        """

        LOGGER.info("Stopping config watches")
        try:
            self._trigger.stop_tasks()
        except Exception as exc:
            LOGGER.info("Error when stopping watcher: {}".format(exc))

    def get_number_of_active_watchers(self) -> int:
        return self._trigger.get_number_of_active_tasks()

    def create_kv_updater_for_path(self, config_path: str) -> KVUpdater:
        return KVUpdater(config_path, self._consul_client)
