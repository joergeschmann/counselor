import logging
import unittest

from src.counselor.config import KVConfigPath

from src.counselor.endpoint.common import Response
from src.counselor.watcher import ReconfigurableService

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestService(ReconfigurableService):
    def __init__(self, service_key: str, config_path: KVConfigPath, current_config: dict = None):
        self.service_key = service_key
        self.config_path = config_path
        self.last_config = current_config
        self.failed_service_check = False

    def get_service_key(self) -> str:
        return self.service_key

    def get_current_config(self) -> dict:
        return self.last_config

    def get_config_path(self) -> str:
        return self.config_path.compose_path()

    def notify_failed_service_check(self, response: Response):
        LOGGER.info("Failed service check: {}".format(response.as_string()))
        self.failed_service_check = True

    def configure(self, config=dict) -> bool:
        LOGGER.info("Configured: {}".format(config))
        self.last_config = config
        self.failed_service_check = False
        return True

    def reconfigure(self, new_config=dict) -> bool:
        LOGGER.info("New configuration received: {}".format(new_config))
        self.configure(new_config)
        return True


if __name__ == '__main__':
    unittest.main()
