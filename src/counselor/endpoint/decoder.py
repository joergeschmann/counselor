import base64
import json
import logging
from typing import List

from .encoder import Encoder
from .entity import ConsulKeyValue, ServiceDefinition

LOGGER = logging.getLogger(__name__)


class Decoder(object):
    """Base class to decode the payload
    """

    def __init__(self):
        self.exception = None
        self.error_message = ""
        self.successful = True

    def decode(self, payload):
        return payload

    def set_error_message(self, message: str = "", exception: Exception = None):
        self.successful = False
        self.error_message = message
        self.exception = exception


class BooleanDecoder(Decoder):
    """Parse the payload into a boolean.
    """

    def decode(self, payload) -> bool:
        return bool(payload)


class JsonDecoder(Decoder):
    """Parse the json payload and return a simple dict.
    """

    def decode(self, payload) -> dict:
        return self._parse_json(payload)

    def _parse_json(self, payload) -> dict:
        result = {}

        if not isinstance(payload, bytes) and not isinstance(payload, str):
            self.set_error_message(
                "To parse the dict, response need to be a string or byte array: {}".format(type(payload)))
            return result

        try:
            result = json.loads(payload, encoding='utf-8')
        except Exception as exc:
            self.set_error_message("Could not unmarshal", exc)

        return result


class ConsulKVDecoder(JsonDecoder):

    def create_kv_from_json(self, parsed_json):
        value = parsed_json.get('Value', {})
        if isinstance(value, str) or isinstance(value, bytes):
            decoded_value = base64.b64decode(value)
            value = json.loads(decoded_value)
        flags = parsed_json.get('Flags', 0)
        if isinstance(flags, int):
            flags = []

        return ConsulKeyValue(
            key=parsed_json.get('Key', ''),
            value=value,
            flags=flags,
            lock_index=parsed_json.get('LockIndex', 0),
            create_index=parsed_json.get('CreateIndex', 0),
            modify_index=parsed_json.get('ModifyIndex', 0)
        )

    def decode(self, payload) -> ConsulKeyValue:
        parsed_json = self._parse_json(payload)

        if isinstance(parsed_json, List):
            if len(parsed_json) == 0:
                return ConsulKeyValue()
            else:
                parsed_json = parsed_json[0]

        return self.create_kv_from_json(parsed_json)


class ConsulKVListDecoder(ConsulKVDecoder):

    def decode(self, payload) -> List[ConsulKeyValue]:
        parsed_json_list = self._parse_json(payload)

        result_list = []
        for e in parsed_json_list:
            result_list.append(self.create_kv_from_json(e))

        return result_list


class ServiceDefinitionDecoder(JsonDecoder):
    """Decode a single ServiceDefinition.
    """

    def decode(self, payload) -> ServiceDefinition:
        json_dict = self._parse_json(payload)
        return Encoder.consul_dict_to_service_definition(json_dict)


class ServiceDefinitionListDecoder(JsonDecoder):
    """Decode a list of ServiceDefinitions.
    """

    def decode(self, payload) -> List[ServiceDefinition]:
        result_list: List[ServiceDefinition] = []
        service_list = self._parse_json(payload)

        # it can either be a list [service1, service2, ...] of services or a dict {key1:service1, key2:service2, ...}
        if isinstance(service_list, dict):
            for key in service_list.keys():
                result_list.append(Encoder.consul_dict_to_service_definition(service_list[key]))
        elif isinstance(service_list, list):
            for e in service_list:
                result_list.append(Encoder.consul_dict_to_service_definition(e))

        return result_list
