import logging

from .encoding import StatusResponse, Encoder, ServiceDefinitionDecoder, Decoder, ServiceDefinition
from .endpoint import Endpoint

LOGGER = logging.getLogger(__name__)


class Service(Endpoint):
    """Service endpoint for Consul.
    """

    CHECK_EXCEPTION = 'check must be a tuple of script, interval, and ttl'

    def register(self, service_definition: ServiceDefinition) -> StatusResponse:
        """Register a service.
        """

        service_definition.validate()
        payload = Encoder.service_definition_to_consul_dict(service_definition)

        status, successful = self._put_response(url_parts=['register'], query=None, payload=payload,
                                                response_parser=Decoder())
        LOGGER.info("Registering successful: {}".format(successful))
        return status

    def get_details(self, service_key) -> (StatusResponse, ServiceDefinition):
        """Get the details of the service.
        """

        return self._get_response(url_parts=[service_key], response_parser=ServiceDefinitionDecoder())

    def deregister(self, service_key) -> StatusResponse:
        """Deregister a service.
        """

        status, successful = self._put_response(url_parts=['deregister', service_key], response_parser=Decoder())
        LOGGER.info("Deregistering successful: {}".format(successful))
        return status
