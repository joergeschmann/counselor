import logging
from datetime import timedelta
from threading import Event

from .client import ConsulClient
from .watcher import Task

LOGGER = logging.getLogger(__name__)


class ConfigUpdateListener:
    """Interface to provide the methods to call, when an update is available"""

    def get_path(self) -> str:
        """Return the KV path to check for updates"""
        pass

    def on_init(self, config: dict) -> bool:
        """Logic to execute when the watcher fetches the config for the first time"""
        return self.on_update(config)

    def on_update(self, new_config: dict) -> bool:
        """Logic to execute when an update is available"""
        pass


class KVWatcherTask(Task):
    """Fetches the config from Consul KV store and notifies the ConfigUpdateListener if there is an update.
    """

    def __init__(self, listener: ConfigUpdateListener, consul_client: ConsulClient, interval: timedelta,
                 stop_event: Event, log_interval_seconds=3 * 60 * 60):
        super().__init__(listener.get_path(), interval, stop_event, log_interval_seconds)
        self.listener = listener
        self.last_modify_index = 0
        self.consul_client = consul_client

    def get_path(self) -> str:
        return self.listener.get_path()

    def check(self):
        self.log_with_interval("Checking kv config: {}".format(self.get_path()))

        try:
            response, new_config = self.consul_client.kv.get(self.get_path())
        except Exception as exc:
            LOGGER.error("Could not check config path {}: {}".format(self.get_path(), exc))
            return

        if not response.successful:
            LOGGER.error("Failed request for path {}: {}".format(self.get_path(), response.as_string()))
            return

        successful = False
        if self.last_modify_index == 0:
            successful = self.listener.on_init(new_config.value)
        elif self.last_modify_index < new_config.modify_index:
            successful = self.listener.on_update(new_config.value)
        else:
            LOGGER.debug("Config still up to date: {}".format(self.last_modify_index))
            return

        if successful:
            self.last_modify_index = new_config.modify_index
            LOGGER.info("Successfully updated to modify index {}".format(self.last_modify_index))
        else:
            LOGGER.error("Reconfiguration was not successful")
