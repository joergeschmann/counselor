import logging
from datetime import timedelta
from threading import Event, Thread

from .client import Consul
from .config import ReconfigurableService
from .endpoint.common import Response

LOGGER = logging.getLogger(__name__)


class Task(Thread):
    """Base class to represent a Task that is executed by a trigger.
    """

    def __init__(self, interval: timedelta, stop_event: Event):
        Thread.__init__(self, daemon=True)
        self.interval = interval
        self.stop_event = stop_event

    def get_name(self):
        """Return a unique name to identify the task
        """
        pass

    def check(self):
        """Method to implement the check that is periodically executed
        """
        pass

    def stop(self):
        self.stop_event.set()
        self.join()

    def run(self):
        while not self.stop_event.wait(self.interval.total_seconds()):
            self.check()


class ServiceWatcherTask(Task):
    """Fetches the service definition from Consul services and notifies the ReconfigurableService if there is an update.
    """

    def __init__(self, service: ReconfigurableService, consul_client: Consul, interval: timedelta, stop_event: Event):
        super().__init__(interval, stop_event)
        self.service = service
        self.last_service_config_hash = ""
        self.consul_client = consul_client

    def get_name(self) -> str:
        return self.service.get_service_key()

    def check(self):
        LOGGER.info("Checking service: {}".format(self.service.get_service_key()))

        try:
            response, new_service_definition = self.consul_client.agent.service.get_details(
                self.service.get_service_key())
        except Exception as exc:
            return self.service.notify_failed_service_check(Response.create_error_result_with_exception_only(exc))

        if not response.successful:
            self.service.notify_failed_service_check(response)
            return

        if self.last_service_config_hash == "":
            self.last_service_config_hash = new_service_definition.content_hash
            return

        if self.last_service_config_hash != new_service_definition.content_hash:
            successful = self.service.reconfigure(new_service_definition.meta)
            if successful:
                self.last_service_config_hash = new_service_definition.content_hash
            else:
                LOGGER.error("Reconfiguration was not successful")


class KVConfigWatcherTask(Task):
    """Fetches the config from Consul KV store and notifies the ReconfigurableService if there is an update.
    """

    def __init__(self, service: ReconfigurableService, consul_client: Consul, interval: timedelta, stop_event: Event):
        super().__init__(interval, stop_event)
        self.service = service
        self.last_modify_index = 0
        self.consul_client = consul_client

    def get_name(self) -> str:
        return self.service.get_service_key()

    def check(self):
        LOGGER.info("Checking service config: {}".format(self.service.get_service_key()))

        try:
            response, new_config = self.consul_client.kv.get(self.service.get_config_path())
        except Exception as exc:
            return self.service.notify_failed_service_check(Response.create_error_result_with_exception_only(exc))

        if not response.successful:
            self.service.notify_failed_service_check(response)
            return

        successful = False
        if self.last_modify_index == 0:
            successful = self.service.configure(new_config.value)
        elif self.last_modify_index < new_config.modify_index:
            successful = self.service.reconfigure(new_config.value)
        else:
            LOGGER.debug("Config still up to date: {}".format(self.last_modify_index))
            return

        if successful:
            self.last_modify_index = new_config.modify_index
        else:
            LOGGER.error("Reconfiguration was not successful")
