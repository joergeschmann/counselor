import logging
import unittest
import uuid
from datetime import timedelta
from threading import Event

from src.counselor.client import Consul
from src.counselor.config import KVConfigPath
from src.counselor.endpoint.common import Response
from src.counselor.endpoint.http_endpoint import EndpointConfig
from src.counselor.watcher import ReconfigurableService, KVConfigWatcherTask

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


class KVConfigWatcherTaskTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.consul_config = EndpointConfig()
        self.consul = Consul(config=self.consul_config)
        self.kv_config_path = KVConfigPath(project="project", domain="feature", service="service",
                                           detail="config", env="dev")

    def tearDown(self):
        LOGGER.info("Cleaning up")
        response = self.consul.kv.delete(self.kv_config_path.compose_path(), recurse=True)
        if not response.successful:
            LOGGER.info("Cound not delete key: {}".format(response.as_string()))

    def test_config_watcher_task(self):
        test_config = {
            "a": 1,
            "b": "x",
            "c": True
        }

        set_response = self.consul.kv.set(self.kv_config_path.compose_path(), test_config)
        self.assertTrue(set_response.successful)

        test_service = TestService(uuid.uuid4().hex, self.kv_config_path, test_config)

        interval = timedelta(seconds=1)
        stop_event = Event()
        task = KVConfigWatcherTask(test_service, self.consul, interval, stop_event)

        task.check()

        self.assertFalse(test_service.failed_service_check)
        self.assertEqual(test_config, test_service.last_config)


if __name__ == '__main__':
    unittest.main()
