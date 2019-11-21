import logging

from .entity import ServiceDefinition

LOGGER = logging.getLogger(__name__)


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
