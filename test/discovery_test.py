import logging
import time
import unittest
import uuid
from datetime import timedelta

from src.counselor import client
from src.counselor.config import KVConfigPath
from src.counselor.discovery import ServiceDiscovery
from src.counselor.endpoint.common import Response
from src.counselor.endpoint.http_endpoint import EndpointConfig
from src.counselor.filter import KeyValuePair
from src.counselor.watcher import ReconfigurableService

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestService(ReconfigurableService):
    def __init__(self, service_key: str, kv_config_path: KVConfigPath, current_config: dict):
        self.service_key = service_key
        self.kv_config_path = kv_config_path
        self.current_config = current_config
        self.failed_service_check = False
        self.updated = False

    def get_config_path(self) -> str:
        return self.kv_config_path.compose_path()

    def get_current_config(self) -> dict:
        return self.current_config

    def get_service_key(self) -> str:
        return self.service_key

    def notify_failed_service_check(self, response: Response):
        LOGGER.info("Failed service check: {}".format(response.as_string()))
        self.failed_service_check = True

    def configure(self, config=dict) -> bool:
        LOGGER.info("Configuring service: {}".format(config))
        self.current_config = config
        self.failed_service_check = False
        self.updated = True
        return True

    def reconfigure(self, new_config=dict) -> bool:
        LOGGER.info("New configuration received: {}".format(new_config))
        self.configure(new_config)
        return True


class ServiceDiscoveryTests(unittest.TestCase):

    def setUp(self):
        LOGGER.info("Setting up")
        self.test_key_prefix = "test"
        self.service_key = uuid.uuid4().hex
        self.consul_config = EndpointConfig()
        self.consul = client.Consul(config=self.consul_config)
        self.service_discovery = ServiceDiscovery.new_service_discovery_with_consul_client(self.consul)

    def tearDown(self):
        LOGGER.info("Cleaning up")
        self.consul.kv.delete(self.test_key_prefix, recurse=True)
        self.consul.agent.service.deregister(self.service_key)

    def test_filter_services(self):
        service_key = uuid.uuid4().hex
        register_status = self.service_discovery.register_service(service_key=service_key, tags=["test", "ts"],
                                                                  meta={
                                                                      "version": "1.0",
                                                                      "foo": "bar",
                                                                  })

        self.assertTrue(register_status.successful,
                        "Could not register service: {}".format(register_status.as_string()))

        search_status, found_services = self.service_discovery.search_for_services(tags=["ts"],
                                                                                   meta=[KeyValuePair('foo', 'bar')])
        self.assertTrue(search_status.successful,
                        "Could not filter for services: {}".format(search_status.as_string()))

        self.assertEqual(1, len(found_services))
        self.assertEqual(found_services[0].meta['foo'], 'bar', "Meta value does not match")

        deregister_status = self.service_discovery.deregister_service(service_key)

        self.assertTrue(deregister_status.successful,
                        "Service deregistration is not successful: {}".format(deregister_status.as_string()))

        search_status, found_services = self.service_discovery.search_for_services(tags=["ts"],
                                                                                   meta=[KeyValuePair('foo', 'bar')])

        self.assertTrue(search_status.successful, "Search was not successful: {}".format(search_status.as_string()))

        self.assertEqual(0, len(found_services))

    def test_kv_config_watch(self):
        kv_config_path = KVConfigPath(self.test_key_prefix, "feature", "service", "detail", "env")
        current_config = {
            "foo": "bar",
            "number": 3.1415,
            "active": True,
            "list": ["one", "two", "three"],
            "map": {"a": 1, "b": 2, "c": 3}
        }

        test_service = TestService(self.service_key, kv_config_path, current_config)
        response, found_config = self.service_discovery.fetch_config_by_path(test_service.get_config_path())
        self.assertFalse(response.successful)
        self.assertIsNone(found_config)

        config_store_response = self.service_discovery.store_config(test_service.get_config_path(), current_config)
        self.assertTrue(config_store_response.successful,
                        "Could not store config: {}".format(config_store_response.as_string()))

        response, found_config = self.service_discovery.fetch_config_by_path(test_service.get_config_path())
        self.assertTrue(response.successful)
        self.assertEqual(current_config, found_config)

        register_status = self.service_discovery.register_service(service_key=test_service.service_key, tags=["test"],
                                                                  meta={
                                                                      "version": "1.0",
                                                                      "status": "active",
                                                                      "base_time": "1573639530",
                                                                  })

        self.assertTrue(register_status.successful,
                        "Could not register service: {}".format(register_status.as_string()))

        self.assertFalse(test_service.failed_service_check, "Service check should not fail before start")
        self.assertIsNotNone(test_service.current_config, "Config should be set")

        interval = timedelta(seconds=1)
        self.service_discovery.add_config_watch(test_service, interval)
        watch_status = self.service_discovery.start_config_watch()
        self.assertTrue(watch_status.successful, "Could not start watcher: {}".format(watch_status.as_string()))

        time.sleep(1.0)

        test_service.current_config["reconfigure_action"] = "restart"
        update_status = self.service_discovery.update_config(test_service.get_config_path(),
                                                             test_service.get_current_config())
        self.assertTrue(update_status.successful, "Update was not successful {}".format(update_status.as_string()))

        time.sleep(5.0)
        self.service_discovery.stop_config_watch()

        self.assertFalse(test_service.failed_service_check, "Check should not fail")
        self.assertIsNotNone(test_service.current_config, "Last config should should be set by the watcher update")
        self.assertTrue(test_service.updated, "Updated flag in service should be true")

        deregister_status = self.service_discovery.deregister_service(self.service_key)
        self.assertTrue(deregister_status.successful,
                        "Could not deregister service: {}".format(deregister_status.as_string()))

        if __name__ == '__main__':
            unittest.main()
