import logging
from typing import List

from .common import Response
from .decoder import ServiceDefinitionDecoder, ServiceDefinitionListDecoder
from .encoder import Encoder
from .entity import ServiceDefinition
from .http_endpoint import HttpEndpoint, EndpointConfig

LOGGER = logging.getLogger(__name__)


class ServiceEndpoint(HttpEndpoint):
    """Service endpoint for Consul. It uses the the agent service endpoint, which is easier than the low level service endpoint.
    """

    def __init__(self, endpoint_config: EndpointConfig, url_parts: List[str] = None):
        if url_parts is None:
            url_parts = ["agent"]
        super().__init__(endpoint_config, url_parts)

    def search(self, query: List[tuple] = None) -> (Response, List[ServiceDefinition]):
        """Return all the services that are registered with the local agent.
        """

        response = self.get_response(url_parts=['services'], query=query)

        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = ServiceDefinitionListDecoder()
        found_services = decoder.decode(response.payload)

        if not decoder.successful:
            return endpoint_response.update_by_decode_result(found_services), None

        return endpoint_response, found_services

    def register(self, service_definition: ServiceDefinition) -> Response:
        """Register a service.
        """

        service_definition.validate()
        payload = Encoder.service_definition_to_consul_dict(service_definition)

        response = self.put_response(url_parts=['service', 'register'], query=None, payload=payload)
        return Response.create_from_http_response(response)

    def get_details(self, service_key) -> (Response, ServiceDefinition):
        """Get the details of the service.
        """

        response = self.get_response(url_parts=['service', service_key])
        endpoint_response = Response.create_from_http_response(response)
        if not endpoint_response.successful:
            return endpoint_response, None

        decoder = ServiceDefinitionDecoder()
        service_definition = decoder.decode(response.payload)
        if not decoder.successful:
            endpoint_response.update_by_decode_result(decoder), None

        return endpoint_response, service_definition

    def update(self, service_definition: ServiceDefinition) -> Response:
        """Update is the same as registering - the values are simply overwritten
        """

        return self.register(service_definition)

    def deregister(self, service_key) -> Response:
        """Deregister a service.
        """

        response = self.put_response(url_parts=['service', 'deregister', service_key])
        return Response.create_from_http_response(response)
