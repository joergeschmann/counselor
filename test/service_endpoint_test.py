import logging
import unittest

from src.counselor.endpoint.entity import ServiceDefinition
from src.counselor.endpoint.http_endpoint import EndpointConfig
from src.counselor.endpoint.service_endpoint import ServiceEndpoint
from src.counselor.filter import Filter, Operators

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.test_service_key = "unit-test-service"
        self.consul_config = EndpointConfig(host="127.0.0.1", port=8500, version="v1")
        self.service_endpoint = ServiceEndpoint(self.consul_config)

    def tearDown(self):
        LOGGER.info("Cleaning up")
        self.service_endpoint.deregister(self.test_service_key)

    def test_services_registration(self):
        service_definition = ServiceDefinition(
            key=self.test_service_key,
            address="127.0.0.1",
            port=61123,
            tags=["unit", "test", "v1"],
            meta={
                "version": "1.0",
                "status": "active",
                "base_time": "1573639530",
            }
        )

        register_status = self.service_endpoint.register(service_definition)
        self.assertTrue(register_status.successful)

        get_status, found_service_definition = self.service_endpoint.get_details(service_definition.key)
        self.assertTrue(get_status.successful, get_status.as_string())
        self.assertEqual(service_definition.key, found_service_definition.key)
        self.assertEqual(service_definition.port, found_service_definition.port)
        self.assertEqual(service_definition.meta["base_time"], found_service_definition.meta["base_time"])

        service_definition.meta["version"] = "v1.1"
        update_status = self.service_endpoint.update(service_definition)
        self.assertTrue(update_status.successful, update_status.as_string())

        get_status, found_service_definition = self.service_endpoint.get_details(service_definition.key)
        self.assertTrue(get_status.successful, get_status.as_string())
        self.assertEqual(service_definition.meta["version"], found_service_definition.meta["version"])

        filter_expression = Filter.new_meta_filter("status", Operators.OPERATOR_EQUALITY, "active").as_expression()
        query_tuple = ('filter', filter_expression)
        filter_tuples = [query_tuple]

        search_status, found_services = self.service_endpoint.search(filter_tuples)
        self.assertTrue(search_status.successful, search_status.as_string())
        self.assertEqual(service_definition.meta["version"], found_services[0].meta["version"])

        deregister_status = self.service_endpoint.deregister(service_definition.key)
        self.assertTrue(deregister_status.successful, deregister_status.as_string())


if __name__ == '__main__':
    unittest.main()
