import logging
from datetime import timedelta
from threading import Event

from .client import Consul
from .endpoint.service import ServiceDefinition
from .trigger import Trigger

LOGGER = logging.getLogger(__name__)


class ReconfigurableService:
    """Interface for a service to be notified by the watcher.
    Extend this class to encapsulate all the logic to reconfigure your service.
    """

    def __init__(self):
        pass

    def notify_failed_service_check(self):
        """If the service fails to fetch the ServiceDefinition from Consul, this method is called.
        """
        pass

    def reconfigure(self, new_config=dict) -> bool:
        """If the ServiceWatcher notices a change, this method is called to give the new configuration.
        """
        pass


class ServiceWatcherTask:
    """Fetches the config from Consul and notifies the ReconfigurableService if there is an update.
    """

    def __init__(self, service: ReconfigurableService, service_definition: ServiceDefinition, consul_client: Consul):
        self.service = service
        self.service_definition = service_definition
        self.last_service_config_hash = ""
        self.consul_client = consul_client

    def get_name(self) -> str:
        return self.service_definition.key

    def check_service(self):
        LOGGER.info("Checking service: {}".format(self.service_definition.key))

        status, new_service_details = self.consul_client.agent.service.get_details(self.service_definition.key)
        if not status.successful:
            self.service.notify_failed_service_check()
            return

        if self.last_service_config_hash == "":
            self.last_service_config_hash = new_service_details.content_hash
            return

        if self.last_service_config_hash != new_service_details.content_hash:
            successful = self.service.reconfigure(new_service_details.meta)
            if successful:
                self.last_service_config_hash = new_service_details.content_hash
            else:
                LOGGER.error("Reconfiguration was not successful")


class ServiceWatcher:
    """Watcher that executes the periodic checks for configuration updates.
    """

    def __init__(self, task: ServiceWatcherTask, interval_seconds: timedelta = timedelta(seconds=5)):
        self.trigger = Trigger()
        self.trigger.add_task(task.get_name(), func=task.check_service, interval=interval_seconds, daemon=True)
        self.running = False

    @staticmethod
    def new_service_watcher_from_task_details(service: ReconfigurableService, service_definition: ServiceDefinition,
                                              consul_client: Consul, check_interval: timedelta) -> 'ServiceWatcher':
        watcher_task = ServiceWatcherTask(service, service_definition, consul_client)
        return ServiceWatcher(watcher_task, check_interval)

    def start_nonblocking(self):
        self.trigger.run()
        self.running = True

    def start_blocking(self, close_event: Event):
        self.start_nonblocking()
        close_event.wait()
        self.stop()

    def stop(self):
        self.trigger.stop_tasks()
        self.running = False
