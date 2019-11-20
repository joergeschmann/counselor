import logging
import time
import unittest
import uuid
from datetime import timedelta

from counselor.endpoint.encoding import StatusResponse
from src.counselor.discovery import ServiceDiscovery
from src.counselor.filter import KeyValuePair
from src.counselor.watcher import ReconfigurableService

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestService(ReconfigurableService):
    def __init__(self):
        super().__init__()
        self.last_config = None
        self.failed_service_check = False

    def notify_failed_service_check(self, response: StatusResponse):
        LOGGER.info("Failed service check: {}".format(response.as_string()))
        self.failed_service_check = True

    def reconfigure(self, new_config=dict) -> bool:
        LOGGER.info("New configuration received: {}".format(new_config))
        self.last_config = new_config
        self.failed_service_check = False
        return True


class TestServiceDiscovery(unittest.TestCase):

    def test_filter_services(self):
        service_discovery = ServiceDiscovery.new_service_discovery_with_default_consul_client()

        register_status = service_discovery.register_service(service_key=uuid.uuid4().hex, tags=["test", "ts"], meta={
            "version": "1.0",
            "foo": "bar",
        })

        self.assertTrue(register_status.successful,
                        "Could not register service: {}".format(register_status.as_string()))

        search_status, found_services = service_discovery.search_for_services(tags=["ts"],
                                                                              meta=[KeyValuePair('foo', 'bar')])
        self.assertTrue(search_status.successful,
                        "Could not filter for services: {}".format(search_status.as_string()))

        self.assertEqual(1, len(found_services))
        self.assertEqual(found_services[0].meta['foo'], 'bar', "Meta value does not match")

        deregister_status = service_discovery.deregister_service()

        self.assertTrue(deregister_status.successful,
                        "Service deregistration is not successful: {}".format(deregister_status.as_string()))

        search_status, found_services = service_discovery.search_for_services(tags=["ts"],
                                                                              meta=[KeyValuePair('foo', 'bar')])

        self.assertTrue(search_status.successful, "Search was not successful: {}".format(search_status.as_string()))

        self.assertEqual(0, len(found_services))

    def test_register_deregister_service_in_catalog(self):
        service_discovery = ServiceDiscovery.new_service_discovery_with_default_consul_client()

        register_status = service_discovery.register_service(service_key=uuid.uuid4().hex, tags=["test"], meta={
            "version": "1.0",
            "status": "active",
            "base_time": "1573639530",
        })

        self.assertTrue(register_status.successful,
                        "Could not register service: {}".format(register_status.as_string()))

        test_service = TestService()
        self.assertFalse(test_service.failed_service_check, "Service check should not fail before start")
        self.assertIsNone(test_service.last_config, "Config should still be None")

        config_update_check_interval_seconds = 1
        watch_status = service_discovery.start_config_watch(test_service,
                                                            timedelta(seconds=config_update_check_interval_seconds))
        self.assertTrue(watch_status.successful, "Could not start watcher: {}".format(watch_status.as_string()))

        time.sleep(1.0)

        service_discovery.service_definition.meta["addition"] = "True"
        update_status = service_discovery.update_service_definition()
        self.assertTrue(update_status.successful, "Update was not successful {}".format(update_status.as_string()))

        time.sleep(5.0)
        service_discovery.stop_config_watch()

        self.assertFalse(test_service.failed_service_check, "Check should not fail")
        self.assertIsNotNone(test_service.last_config, "Last config should should be set by the watcher update")
        self.assertEqual(service_discovery.service_definition.meta["addition"],
                         test_service.last_config["addition"])

        deregister_status = service_discovery.deregister_service()
        self.assertTrue(deregister_status.successful,
                        "Could not deregister service: {}".format(deregister_status.as_string()))


if __name__ == '__main__':
    unittest.main()
