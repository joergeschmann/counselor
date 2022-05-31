import logging
import time
import unittest
import uuid
from datetime import timedelta
from threading import Event

from counselor import client
from counselor.discovery import ServiceDiscovery, ReconfigurableService
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.endpoint.kv_endpoint import KVPath
from counselor.filter import KeyValuePair
from counselor.kv_watcher import ConfigUpdateListener

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class ServiceConfigUpdateListener(ConfigUpdateListener):
    def __init__(self, kv_path: str, current_config: dict = None):
        self.kv_path = kv_path
        self.current_config = current_config
        self.initialized = False
        self.updated = False

    def get_path(self) -> str:
        return self.kv_path

    def on_init(self, config: dict) -> bool:
        for key in config.keys():
            self.current_config[key] = config[key]
        LOGGER.info("init: {}".format(config))
        self.initialized = True
        return True

    def on_update(self, new_config: dict) -> bool:
        self.current_config = new_config
        LOGGER.info("update: {}".format(new_config))
        self.updated = True
        return True


class ServiceDiscoveryTests(unittest.TestCase):

    def setUp(self):
        LOGGER.info("Setting up")
        self.test_key_prefix = "test"
        self.service_key = uuid.uuid4().hex
        self.consul_config = EndpointConfig(token='')
        self.consul = client.ConsulClient(config=self.consul_config)
        self.service_discovery = ServiceDiscovery.new_service_discovery_with_consul_client(self.consul)

        self.kv_path = KVPath(self.test_key_prefix, "unit-test", "test")
        self.tags = ["test", "ts"]
        self.service_meta = {
            "version": "1.0",
            "foo": "bar",
        }
        self.service = ReconfigurableService(service_key=self.service_key,
                                             config_path=self.kv_path,
                                             tags=self.tags,
                                             meta=self.service_meta)

    def tearDown(self):
        LOGGER.info("Cleaning up")
        self.consul.kv.delete(self.test_key_prefix, recurse=True)
        self.consul.service.deregister(self.service_key)

    def test_filter_services(self):
        register_status = self.service_discovery.register_service(self.service.to_service_definition())
        self.assertTrue(register_status.successful,
                        "Could not register service: {}".format(register_status.as_string()))

        search_status, found_services = self.service_discovery.search_for_services(tags=["ts"],
                                                                                   meta=[KeyValuePair('foo', 'bar')])
        self.assertTrue(search_status.successful,
                        "Could not filter for services: {}".format(search_status.as_string()))

        self.assertEqual(1, len(found_services))
        self.assertEqual(found_services[0].meta['foo'], 'bar', "Meta value does not match")

        deregister_status = self.service_discovery.deregister_service(self.service_key)

        self.assertTrue(deregister_status.successful,
                        "Service deregistration is not successful: {}".format(deregister_status.as_string()))

        search_status, found_services = self.service_discovery.search_for_services(tags=["ts"],
                                                                                   meta=[KeyValuePair('foo', 'bar')])

        self.assertTrue(search_status.successful, "Search was not successful: {}".format(search_status.as_string()))

        self.assertEqual(0, len(found_services))

    def test_kv_config_watch(self):
        response, found_config = self.service_discovery.fetch_config_by_path(self.service.compose_config_path())
        self.assertFalse(response.successful, response.as_string())
        self.assertIsNone(found_config)

        self.service.current_config = {
            "foo": "bar",
            "number": 3.1415,
            "active": True,
            "list": ["one", "two", "three"],
            "map": {"a": 1, "b": 2, "c": 3}
        }

        config_store_response = self.service_discovery.store_config(self.service.compose_config_path(),
                                                                    self.service.current_config)
        self.assertTrue(config_store_response.successful,
                        "Could not store config: {}".format(config_store_response.as_string()))

        response, found_config = self.service_discovery.fetch_config_by_path(self.service.compose_config_path())
        self.assertTrue(response.successful, response.as_string())
        self.assertEqual(self.service.current_config, found_config)

        register_status = self.service_discovery.register_service(self.service.to_service_definition())

        self.assertTrue(register_status.successful,
                        "Could not register service: {}".format(register_status.as_string()))

        config_update_listener = ServiceConfigUpdateListener(self.service.compose_config_path(),
                                                             self.service.current_config)
        interval = timedelta(seconds=1)
        stop_event = Event()
        self.service_discovery.add_config_watch(config_update_listener, interval, stop_event)
        watch_status = self.service_discovery.start_config_watch()
        self.assertTrue(watch_status.successful, "Could not start watcher: {}".format(watch_status.as_string()))

        time.sleep(1.0)

        reconfigure_config_key = "reconfigure_action"
        reconfigure_config_value = "restart"
        kv_updater = self.service_discovery.create_kv_updater_for_path(self.service.compose_config_path())
        update_status = kv_updater.merge({reconfigure_config_key: reconfigure_config_value})
        self.assertTrue(update_status.successful, "Update was not successful {}".format(update_status.as_string()))

        time.sleep(5.0)
        self.service_discovery.stop_config_watch()

        self.assertIsNotNone(self.service.current_config, "Last config should should be set by the watcher update")
        self.assertTrue(config_update_listener.updated, "Updated flag in service should be true")
        self.assertEqual(reconfigure_config_value, config_update_listener.current_config[reconfigure_config_key])

        deregister_status = self.service_discovery.deregister_service(self.service_key)
        self.assertTrue(deregister_status.successful,
                        "Could not deregister service: {}".format(deregister_status.as_string()))

        self.assertEqual(0, self.service_discovery.get_number_of_active_watchers())

        if __name__ == '__main__':
            unittest.main()
