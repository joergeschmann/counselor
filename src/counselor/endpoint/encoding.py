import json
from typing import List

from .http import Response


class ServiceDefinition:
    """This class holds an internal representation of the Consul structure for a service.
    """

    def __init__(self, key: str, address=None, port=0, tags=None, meta=None, content_hash=None):
        if tags is None:
            tags = []
        if meta is None:
            meta = {}

        self.key = key
        self.address = address
        self.port = port
        self.tags = tags
        self.meta = meta
        self.content_hash = content_hash
        self.check = None
        self.interval = None
        self.ttl = None
        self.httpcheck = None

    @staticmethod
    def new_simple_service_definition(key: str, tags=None, meta=None):
        return ServiceDefinition(key=key, tags=tags, meta=meta)

    def validate(self):
        if self.port and not isinstance(self.port, int):
            raise ValueError('port must be an integer')
        elif self.tags and not isinstance(self.tags, list):
            raise ValueError('tags must be a list of strings')
        elif (self.check or self.httpcheck) and self.ttl:
            raise ValueError('Can not specify both a check and ttl')

        if (self.check or self.httpcheck) and not self.interval:
            raise ValueError('An interval is required for check scripts and http checks.')

    def as_json(self) -> str:
        return json.dumps(self.__dict__)


class StatusResponse:
    """StatusResponse is used as a standard response to indicate whether a request to Consul was successful or not.
    """

    def __init__(self, successful=True, kind="", message=""):
        self.successful = successful
        self.kind = kind
        self.message = message

    @staticmethod
    def new_successful_result():
        return StatusResponse()

    @staticmethod
    def new_error_result(kind="", message=""):
        return StatusResponse(successful=False, kind=kind, message=message)

    @staticmethod
    def new_error_result_with_message_only(message=""):
        return StatusResponse.new_error_result(message=message)

    @staticmethod
    def new_status_from_response(response: Response):
        if response.is_successful():
            return StatusResponse(kind=response.status_code)
        else:
            return StatusResponse.new_error_result(kind=response.status_code, message=response.payload)

    def as_string(self) -> str:
        return "successful: {} - {}: {}".format(self.successful, self.kind, self.message)


class Encoder(object):
    """The Encoder transforms a ServiceDefinition into the Consul structure.

    """

    def __init__(self):
        pass

    @staticmethod
    def service_definition_to_consul_dict(service_definition: ServiceDefinition) -> dict:
        service_definition = {
            'ID': service_definition.key,
            'Name': service_definition.key,
            'Port': service_definition.port,
            'Address': service_definition.address,
            'Tags': service_definition.tags,
            'Meta': service_definition.meta,
            'ContentHash': service_definition.content_hash
        }

        for key in list(service_definition.keys()):
            if service_definition[key] is None:
                del service_definition[key]

        return service_definition

    @staticmethod
    def consul_dict_to_service_definition(consul_response: dict) -> ServiceDefinition:
        return ServiceDefinition(
            consul_response.get('ID', ''),
            consul_response.get('Address', ''),
            consul_response.get('Port', ''),
            consul_response.get('Tags', ''),
            consul_response.get('Meta', ''),
            consul_response.get("ContentHash", '')
        )


class Decoder(object):
    """Depending on the API call, Consul responds with specific structures.
    This class acts as a base to decode the response.
    """

    def decode(self, response: Response):
        return StatusResponse.new_status_from_response(response), response.payload


class ServiceDefinitionDecoder(Decoder):
    """Decode a single ServiceDefinition.
    """

    def decode(self, response: Response) -> (StatusResponse, ServiceDefinition):
        if response.is_successful():
            return StatusResponse.new_successful_result(), Encoder.consul_dict_to_service_definition(
                response.payload)

        return StatusResponse.new_status_from_response(response), None


class ServiceDefinitionListDecoder(Decoder):
    """Decode a list of ServiceDefinitions.
    """

    def decode(self, response: Response) -> (StatusResponse, List[ServiceDefinition]):
        result_list: List[ServiceDefinition] = []

        if response.is_successful():
            if isinstance(response.payload, dict):
                for key in response.payload.keys():
                    result_list.append(Encoder.consul_dict_to_service_definition(response.payload[key]))
            elif isinstance(response.payload, list):
                for e in response.payload:
                    result_list.append(Encoder.consul_dict_to_service_definition(e))

            return StatusResponse.new_successful_result(), result_list

        return StatusResponse.new_status_from_response(response), result_list
