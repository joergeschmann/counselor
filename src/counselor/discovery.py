import logging
from datetime import timedelta
from threading import Event
from typing import List

from .client import Consul
from .config import ReconfigurableService
from .endpoint.common import Response
from .endpoint.entity import ServiceDefinition
from .endpoint.http_endpoint import EndpointConfig
from .filter import KeyValuePair, Filter, Operators
from .trigger import Trigger
from .watcher import KVConfigWatcherTask

LOGGER = logging.getLogger(__name__)


class ServiceDiscovery:
    """Facade to interact with Consul. The use case is that you have a service you want to register in Consul.
    The service definition is stored to the service module, whereas the configuration for the service is persisted in
    the Consul KV store. After your service is registered, you can start a config watcher, that periodically
    fetches the config from Consul KV store. If there is a change in the configuration, the service is notified
    via ReconfigurableService interface to reconfigure itself.
    """

    def __init__(self, client: Consul):
        self._consul = client
        self._trigger = Trigger()

    @staticmethod
    def new_service_discovery_with_defaults() -> 'ServiceDiscovery':
        return ServiceDiscovery.new_service_discovery_with_consul_config(EndpointConfig())

    @staticmethod
    def new_service_discovery_with_consul_config(config: EndpointConfig) -> 'ServiceDiscovery':
        return ServiceDiscovery.new_service_discovery_with_consul_client(Consul(config))

    @staticmethod
    def new_service_discovery_with_consul_client(client: Consul) -> 'ServiceDiscovery':
        return ServiceDiscovery(client)

    @staticmethod
    def new_service_discovery_with_config_details(consul_ip: str = "127.0.0.1",
                                                  consul_port: int = 8500) -> 'ServiceDiscovery':
        return ServiceDiscovery.new_service_discovery_with_consul_config(
            EndpointConfig(host=consul_ip, port=consul_port))

    def fetch_config_by_path(self, path: str) -> (Response, dict):
        return self._consul.kv.get_raw(path)

    def store_config(self, path: str, config: dict) -> Response:
        """Store the config in Consul.
        """
        return self._consul.kv.set(path, config)

    def update_config(self, path: str, config: dict) -> Response:
        """Update the config in Consul.
        """
        return self._consul.kv.set(path, config)

    def update_config_by_service(self, service: ReconfigurableService) -> Response:
        return self.update_config(service.get_config_path(), service.get_current_config())

    def register_service(self, service_key: str, tags=None, meta=None) -> Response:
        """Register a ServiceDefinition in Consul.
        """

        LOGGER.info("Registering service definition {}".format(service_key))

        service_definition = ServiceDefinition(key=service_key, tags=tags, meta=meta)

        return self._update_service_definition(service_definition)

    def get_service_details(self, service_key) -> (Response, ServiceDefinition):
        return self._consul.agent.service.get_details(service_key)

    def register_service_and_store_config(self, reconfigurable_service: ReconfigurableService, tags: List[str],
                                          meta: dict) -> Response:
        register_response = self.register_service(reconfigurable_service.get_service_key(), tags, meta)
        if not register_response.successful:
            return register_response

        return self.store_config(reconfigurable_service.get_config_path(), reconfigurable_service.get_current_config())

    def update_service(self, service_key: str, tags: List[str] = None, meta: dict = None) -> Response:
        """Update the ServiceDefinition in Consul.
        Update is the same as a registration.
        """
        LOGGER.info("Updating service definition {}".format(service_key))

        service_definition = ServiceDefinition(key=service_key, tags=tags, meta=meta)

        return self._update_service_definition(service_definition)

    def _update_service_definition(self, service_definition: ServiceDefinition) -> Response:
        return self._consul.agent.service.register(service_definition)

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

            return self._consul.agent.service.deregister(service_key)
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

        return self._consul.agent.services(filter_tuples)

    def add_multiple_config_watches(self, services: List[ReconfigurableService], check_interval: timedelta,
                                    stop_event=Event()):
        """Add a list of config watchers
        """

        if services is None or len(services) == 0:
            return

        for service in services:
            if service is None:
                continue

            LOGGER.info("Adding config watch for {}".format(service.get_service_key()))
            watcher_task = KVConfigWatcherTask(service, self._consul, check_interval, stop_event)
            self._trigger.add_task(watcher_task)

    def add_config_watch(self, service: ReconfigurableService, check_interval: timedelta,
                         stop_event=Event()):
        """Create a watcher that periodically checks for config changes.
        """

        self.add_multiple_config_watches(services=[service], check_interval=check_interval, stop_event=stop_event)

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
