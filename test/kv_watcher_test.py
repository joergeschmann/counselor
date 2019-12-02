import logging
import unittest
from datetime import timedelta
from threading import Event

from counselor.client import ConsulClient
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.endpoint.kv_endpoint import KVPath
from counselor.kv_watcher import ConfigUpdateListener, KVWatcherTask

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestListener(ConfigUpdateListener):
    def __init__(self, kv_path: KVPath):
        self.kv_path = kv_path
        self.initialized = False
        self.updated = False
        self.current_config = None

    def get_path(self) -> str:
        return self.kv_path.compose_path()

    def on_init(self, config: dict) -> bool:
        self.current_config = config
        self.initialized = True
        return True

    def on_update(self, new_config: dict) -> bool:
        self.current_config = new_config
        self.updated = True
        return True


class KVWatcherTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.consul_config = EndpointConfig()
        self.consul_client = ConsulClient(config=self.consul_config)
        self.kv_config_path = KVPath(project="project", domain="feature", service="service",
                                     detail="config", env="dev")

    def tearDown(self):
        LOGGER.info("Cleaning up")
        response = self.consul_client.kv.delete(self.kv_config_path.compose_path(), recurse=True)
        if not response.successful:
            LOGGER.info("Cound not delete key: {}".format(response.as_string()))

    def test_config_listener(self):
        test_config = {
            "a": 1,
            "b": "x",
            "c": True
        }

        set_response = self.consul_client.kv.merge(self.kv_config_path.compose_path(), test_config)
        self.assertTrue(set_response.successful)

        test_listener = TestListener(self.kv_config_path)

        interval = timedelta(seconds=1)
        stop_event = Event()

        watcher_task = KVWatcherTask(test_listener, self.consul_client, interval, stop_event)
        watcher_task.check()

        self.assertTrue(test_listener.initialized)
        self.assertFalse(test_listener.updated)
        self.assertEqual(test_config, test_listener.current_config)
        self.assertTrue(watcher_task.last_modify_index > 0)


if __name__ == '__main__':
    unittest.main()
