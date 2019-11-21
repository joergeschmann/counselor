import logging
import unittest

from src.counselor import client

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class KeyValueTests(unittest.TestCase):
    def setUp(self):
        LOGGER.info("Setting up")
        self.test_key_prefix = "test/unit"
        self.consul_config = client.ConsulConfig()
        self.consul = client.Consul(config=self.consul_config)

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

        get_response, found_entry = self.consul.kv.get(key)
        self.assertTrue(get_response.successful)
        self.assertEqual(test_config, found_entry.value, "Configs do not match")


if __name__ == '__main__':
    unittest.main()
