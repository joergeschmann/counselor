import logging
import unittest

from src.counselor import client
from src.counselor.endpoint.encoder import ServiceDefinition

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class AgentTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.test_service_key = "unit-test-service"
        self.consul_config = client.ConsulConfig()
        self.consul = client.Consul(config=self.consul_config)

    def tearDown(self):
        LOGGER.info("Cleaning up")
        self.consul.agent.service.deregister(self.test_service_key)

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

        register_status = self.consul.agent.service.register(service_definition)
        LOGGER.info("Registration status: {}".format(register_status.as_string()))

        get_status, found_service_definition = self.consul.agent.service.get_details(service_definition.key)
        LOGGER.info("Get details status: {}".format(get_status.as_string()))
        LOGGER.info(found_service_definition.as_json())

        service_definition.meta["version"] = "v1.1"
        update_status = self.consul.agent.service.register(service_definition)
        LOGGER.info("Update status: {}".format(update_status.as_string()))

        search_status, found_services = self.consul.agent.services()
        LOGGER.info("Search services status: {}".format(search_status.as_string()))
        LOGGER.info("Versions: {} - {}".format(service_definition.meta["version"], found_services[0].meta["version"]))

        deregister_status = self.consul.agent.service.deregister(service_definition.key)
        LOGGER.info("Deregister status: {}".format(deregister_status.as_string()))


if __name__ == '__main__':
    unittest.main()
