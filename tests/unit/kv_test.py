import unittest

from counselor.endpoint.decoder import JsonDecoder


class KeyValueTestCase(unittest.TestCase):

    def test_decoder(self):
        json_bytes = b'{"foo": "bar", "number": 3.1415, "active": false, "list": ["one", "two", "three"], "map": {"a": 1, "b": 2, "c": 3}}'
        decoder = JsonDecoder()
        result = decoder.decode(json_bytes)
        self.assertTrue(decoder.successful)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
