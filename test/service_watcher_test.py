import logging
import unittest
from datetime import timedelta
from threading import Event

from counselor.client import ConsulClient
from counselor.endpoint.entity import ServiceDefinition
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.service_watcher import ServiceUpdateListener, ServiceWatcherTask

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestListener(ServiceUpdateListener):
    def __init__(self, service_key):
        self.service_key = service_key
        self.initialized = False
        self.updated = False
        self.current_service_definition: ServiceDefinition = None

    def get_service_key(self) -> str:
        return self.service_key

    def on_init(self, service_definition: ServiceDefinition) -> bool:
        self.initialized = True
        self.current_service_definition = service_definition
        return True

    def on_update(self, service_definition: ServiceDefinition) -> bool:
        self.updated = True
        self.current_service_definition = service_definition
        return True


class ServiceWatcherTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.consul_config = EndpointConfig()
        self.consul_client = ConsulClient(config=self.consul_config)
        self.service_key = "service-watcher-test-service"

    def tearDown(self):
        LOGGER.info("Cleaning up")
        response = self.consul_client.service.deregister(self.service_key)
        if not response.successful:
            LOGGER.info("Cound not deregister service: {}".format(response.as_string()))

    def test_service_listener(self):
        meta = {
            "version": "v1.0.0",
            "status": "Serving"
        }
        service_definition = ServiceDefinition(key=self.service_key, tags=["unit-test"], meta=meta)
        register_response = self.consul_client.service.register(service_definition)
        self.assertTrue(register_response.successful, register_response.as_string())

        update_listener = TestListener(self.service_key)
        interval = timedelta(seconds=1)
        stop_event = Event()
        service_watcher_task = ServiceWatcherTask(listener=update_listener, consul_client=self.consul_client,
                                                  interval=interval, stop_event=stop_event)

        service_watcher_task.check()
        self.assertTrue(update_listener.initialized)
        self.assertFalse(update_listener.updated)
        self.assertEqual(meta, update_listener.current_service_definition.meta)

        meta["status"] = "OnHold"
        update_response = self.consul_client.service.update(service_definition)
        self.assertTrue(update_response.successful)

        service_watcher_task.check()
        self.assertTrue(update_listener.updated)
        self.assertEqual(meta, update_listener.current_service_definition.meta)


if __name__ == '__main__':
    unittest.main()
