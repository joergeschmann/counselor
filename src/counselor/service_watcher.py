import logging
from datetime import timedelta
from threading import Event

from .client import ConsulClient
from .endpoint.entity import ServiceDefinition
from .watcher import Task

LOGGER = logging.getLogger(__name__)


class ServiceUpdateListener:
    def get_service_key(self) -> str:
        """Return a unique service key to identify your service
        """
        pass

    def on_init(self, service_definition: ServiceDefinition) -> bool:
        """Logic to execute the first time the watcher fetches the service definition"""
        return self.on_update(service_definition)

    def on_update(self, service_definition: ServiceDefinition) -> bool:
        """Logic to execute when an update is available"""
        pass


class ServiceWatcherTask(Task):
    """Fetches the service definition from Consul services and notifies the ServiceUpdateListener if there is an update.
    """

    def __init__(self, listener: ServiceUpdateListener, consul_client: ConsulClient, interval: timedelta,
                 stop_event: Event, log_interval_seconds=3 * 60 * 60):
        super().__init__(listener.get_service_key(), interval, stop_event, log_interval_seconds)
        self.listener = listener
        self.last_service_config_hash = ""
        self.consul_client = consul_client

    def get_service_key(self) -> str:
        return self.listener.get_service_key()

    def check(self):
        self.log_with_interval("Checking service: {}".format(self.get_service_key()))

        try:
            response, new_service_definition = self.consul_client.service.get_details(
                self.get_service_key())
        except Exception as exc:
            LOGGER.error("Could not check service definition for {}: {}".format(self.get_service_key(), exc))
            return

        if not response.successful:
            LOGGER.error(
                "Failed request for service definition {}: {}".format(self.get_service_key(), response.as_string()))
            return

        successful = False
        if self.last_service_config_hash == "":
            successful = self.listener.on_init(new_service_definition)

        elif self.last_service_config_hash != new_service_definition.content_hash:
            successful = self.listener.on_update(new_service_definition)

        if successful:
            self.last_service_config_hash = new_service_definition.content_hash
            LOGGER.info("Successfully updated to config hash {}".format(self.last_service_config_hash))
        else:
            LOGGER.error("Reconfiguration was not successful")
