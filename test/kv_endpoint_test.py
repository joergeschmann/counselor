import json
import logging
import unittest

from src.counselor import client
from src.counselor.endpoint.http_endpoint import EndpointConfig

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class KeyValueTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.test_key_prefix = "test"
        self.consul_config = EndpointConfig(token="")
        self.consul = client.ConsulClient(config=self.consul_config)

    def tearDown(self):
        LOGGER.info("Cleaning up")
        response = self.consul.kv.delete(self.test_key_prefix, recurse=True)
        if not response.successful:
            LOGGER.info("Cound not delete key: {}".format(response.as_string()))

    def test_kv_raw_entry(self):
        test_config = {
            "key": "value",
            "active": True,
            "pairs": ["btc", "etc", "ren"],
            "strategy": {
                "goal": 42,
                "risk": 3.1415,
            }
        }

        key = self.test_key_prefix + "/raw"

        set_response = self.consul.kv.set(key, test_config)
        self.assertTrue(set_response.successful)

        get_response, found_entry = self.consul.kv.get_raw(key)
        self.assertTrue(get_response.successful)
        self.assertEqual(test_config, found_entry, "Configs do not match")

    def test_kv_consul_entry(self):
        test_config = {
            "key": "value",
            "active": True,
            "pairs": ["btc", "etc", "ren"],
            "strategy": {
                "goal": 42,
                "risk": 3.1415,
            }
        }

        key = self.test_key_prefix + "/config"

        set_response = self.consul.kv.set(key, test_config)
        self.assertTrue(set_response.successful)

        updates = {"active": False, "strategy": {"goal": "none"}}
        merge_response = self.consul.kv.merge(key, updates)
        self.assertTrue(merge_response)

        get_response, found_entry = self.consul.kv.get_raw(key)
        self.assertTrue(get_response.successful)
        self.assertNotEqual(test_config, found_entry, "Configs should diverge")
        self.assertEqual(test_config.get("pairs"), found_entry.get("pairs"))
        self.assertEqual(updates.get("active"), found_entry.get("active"))

    def test_recursive_kv(self):
        service_config_path = key = self.test_key_prefix + "/service"
        service_config = {
            "env": "test",
            "pairs": ["btc", "etc", "ren"],
            "strategy": {
                "goal": 42,
                "risk": 3.1415,
            }
        }
        response = self.consul.kv.set(service_config_path, service_config)
        self.assertTrue(response.successful, response.as_string())

        s1_config_path = service_config_path + "/s1"
        s1_config = {
            "name": "service-1",
            "current_rate": 1.8
        }
        response = self.consul.kv.set(s1_config_path, s1_config)
        self.assertTrue(response.successful, response.as_string())

        s2_config_path = service_config_path + "/s2"
        s2_config = {
            "name": "service-2",
            "current_rate": 1.4
        }
        response = self.consul.kv.set(s2_config_path, s2_config)
        self.assertTrue(response.successful, response.as_string())

        query_params = {"recurse": True}
        http_response = self.consul.kv._get(path=service_config_path, query_params=query_params)
        self.assertTrue(http_response.is_successful())

        parsed_config = json.loads(http_response.payload)
        self.assertEqual(3, len(parsed_config))


if __name__ == '__main__':
    unittest.main()
