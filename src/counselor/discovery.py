import logging
from datetime import timedelta
from threading import Event
from typing import List

from .client import Consul, ConsulConfig
from .config import ReconfigurableService
from .endpoint.common import Response
from .endpoint.service import ServiceDefinition
from .filter import Filter, KeyValuePair, Operators
from .trigger import Trigger
from .watcher import KVConfigWatcherTask

LOGGER = logging.getLogger(__name__)


class ServiceDiscovery:
    """Facade to interact with Consul. The use case is that you have a service you want to register in Consul.
    The configuration for the service is stored in the meta field. After your service is registered,
    you can start a config watcher, that periodically fetches the entry from Consul. If there is a change in the
    configuration, the service is notified via ReconfigurableService interface to reconfigure itself.
    """

    def __init__(self, consul_config=ConsulConfig()):
        self._consul = Consul(consul_config)
        self._service_definition = None
        self._trigger = None
        # TODO: set the stop event from arguments
        self._stop_event = Event()

    @staticmethod
    def new_service_discovery_with_default_consul_client():
        return ServiceDiscovery(ConsulConfig())

    def fetch_config(self, service: ReconfigurableService) -> bool:
        """Fetch the config from consul to initially configure your service
        """
        response, found_config = self._consul.kv.get_raw(service.config_path.compose_path())
        if not response.successful or found_config is None:
            return False

        service.reconfigure(found_config)

    def store_config(self, service: ReconfigurableService) -> Response:
        """Store the config in Consul
        """
        return self._consul.kv.set(service.config_path.compose_path(), service.current_config)

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

    def register_service(self, service_key: str, tags=None, meta=None) -> Response:
        """Register a ServiceDefinition in Consul.
        """

        self._service_definition = ServiceDefinition.new_simple_service_definition(service_key, tags, meta)
        return self.update_service_definition()

    def update_service_definition(self) -> Response:
        """Update the ServiceDefinition in Consul.
        """

        LOGGER.info("Updating definition {}".format(self._service_definition.key))
        return self._consul.agent.service.register(self._service_definition)

    def deregister_service(self) -> Response:
        """Delete the ServiceDefinition in Consul. Also stops the watcher if still active.
        """

        LOGGER.info("Deregistering service {}".format(self._service_definition.key))

        try:
            if self._trigger is not None and self._trigger.running:
                LOGGER.info("Stopping config watch first")
                self.stop_config_watch()

            return self._consul.agent.service.deregister(self._service_definition.key)
        except Exception as exc:
            return Response.create_error_result_with_message_only("{}".format(exc))

    def start_config_watch(self, service: ReconfigurableService, check_interval: timedelta) -> Response:
        """Create a watcher that periodically checks for config changes.
        """

        LOGGER.info("Starting config watch for {}".format(service.service_key))

        try:
            watcher_task = KVConfigWatcherTask(service, self._consul, check_interval, self._stop_event)
            self._trigger = Trigger()
            self._trigger.add_task(watcher_task)
            self._trigger.run_nonblocking()
        except Exception as exc:
            return Response.create_error_result_with_message_only("{}".format(exc))

        return Response.create_successful_result()

    def stop_config_watch(self):
        """Stop the watcher.
        """

        LOGGER.info("Stopping config watch for {}".format(self._service_definition.key))
        try:
            self._stop_event.set()
            self._trigger.stop_tasks()
        except Exception as exc:
            LOGGER.info("Error when stopping watcher: {}".format(exc))
