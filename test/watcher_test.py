import logging
import unittest
import uuid
from datetime import timedelta
from threading import Event

from counselor.client import ConsulConfig, Consul
from counselor.config import KVConfigPath
from counselor.endpoint.common import Response
from counselor.watcher import ReconfigurableService, KVConfigWatcherTask

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestService(ReconfigurableService):
    def __init__(self, service_key: str, config_path: KVConfigPath, current_config: dict = None):
        super().__init__(service_key, config_path, current_config)
        self.last_config = None
        self.failed_service_check = False

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


class KVConfigWatcherTaskTest(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.consul_config = ConsulConfig()
        self.consul = Consul(config=self.consul_config)
        self.kv_config_path = KVConfigPath(project="project", feature="feature", service="service",
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

        test_service = TestService(uuid.uuid4().hex, self.kv_config_path)

        interval = timedelta(seconds=1)
        stop_event = Event()
        task = KVConfigWatcherTask(test_service, self.consul, interval, stop_event)

        task.check()

        self.assertFalse(test_service.failed_service_check)
        self.assertEqual(test_config, test_service.last_config)


if __name__ == '__main__':
    unittest.main()
