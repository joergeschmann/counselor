import logging
from datetime import timedelta
from typing import List

from .client import Consul, ConsulConfig
from .endpoint.encoding import StatusResponse
from .endpoint.service import ServiceDefinition
from .filter import Filter, KeyValuePair, Operators
from .watcher import ServiceWatcher, ReconfigurableService

LOGGER = logging.getLogger(__name__)


class ServiceDiscovery:
    """Facade to interact with Consul. The use case is that you have a service you want to register in Consul.
    The configuration for the service is stored in the meta field. After your service is registered,
    you can start a config watcher, that periodically fetches the entry from Consul. If there is a change in the
    configuration, the service is notified via ReconfigurableService interface to reconfigure itself.
    """

    def __init__(self, consul_config=ConsulConfig()):
        self.consul = Consul(consul_config)
        self.service_definition = None
        self.config_watch = None

    @staticmethod
    def new_service_discovery_with_default_consul_client():
        return ServiceDiscovery(ConsulConfig())

    def load_service(self, key: str) -> StatusResponse:
        """Activats an existing ServiceDefinition from Consul.
        """

        status_response, service_definition = self.consul.agent.service.get_details(key)
        if status_response.successful:
            self.service_definition = service_definition

        return status_response

    def get_active_service_key(self) -> str:
        """Return the key of the active ServiceDefinition.
        """

        if self.service_definition is None:
            return ""
        else:
            return self.service_definition.key

    def search_for_services(self, tags: List[str] = None, meta: List[KeyValuePair] = None) -> (
            StatusResponse, List[ServiceDefinition]):
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

        return self.consul.agent.services(filter_tuples)

    def register_service(self, service_key: str, tags=None, meta=None) -> StatusResponse:
        """Register a ServiceDefinition in Consul.
        """

        self.service_definition = ServiceDefinition.new_simple_service_definition(service_key, tags, meta)
        return self.update_service_definition()

    def update_service_definition(self) -> StatusResponse:
        """Update the ServiceDefinition in Consul. For example if you want to update the configuration.
        """

        LOGGER.info("Updating definition {}".format(self.service_definition.key))
        return self.consul.agent.service.register(self.service_definition)

    def deregister_service(self) -> StatusResponse:
        """Delete the ServiceDefinition in Consul. Also stops the watcher if still active.
        """

        LOGGER.info("Deregistering service {}".format(self.service_definition.key))

        try:
            if self.config_watch is not None and self.config_watch.running:
                LOGGER.info("Stopping config watch first")
                self.stop_config_watch()

            return self.consul.agent.service.deregister(self.service_definition.key)
        except Exception as exc:
            return StatusResponse.new_error_result_with_message_only("{}".format(exc))

    def start_config_watch(self, service: ReconfigurableService, check_interval: timedelta) -> StatusResponse:
        """Create a watcher that periodically checks for config changes.
        """

        LOGGER.info("Starting config watch for {}".format(self.service_definition.key))
        if self.service_definition is None:
            return StatusResponse.new_error_result_with_message_only("No service registered")

        try:
            self.config_watch = ServiceWatcher.new_service_watcher_from_task_details(service, self.service_definition,
                                                                                     self.consul, check_interval)
            self.config_watch.start_nonblocking()
        except Exception as exc:
            return StatusResponse.new_error_result_with_message_only("{}".format(exc))

        return StatusResponse.new_successful_result()

    def stop_config_watch(self):
        """Stop the watcher.
        """

        LOGGER.info("Stopping config watch for {}".format(self.service_definition.key))
        try:
            self.config_watch.stop()
        except Exception as exc:
            LOGGER.info("Error when stopping watcher: {}".format(exc))
