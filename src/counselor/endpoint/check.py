from .common import Response
from .http_endpoint import HttpEndpoint


class Check(HttpEndpoint):
    """
        At the moment checks are implemented as periodic http requests with our own watcher implementation.
        The next step is to involve the consul agent.
        TODO: implement
    """

    def register(self, name, script=None, check_id=None, interval=None, ttl=None, notes=None, http=None):
        response = self.put_response(url_parts=['register'], query=None, payload={
            'ID': check_id,
            'Name': name,
            'Notes': notes,
            'Script': script,
            'HTTP': http,
            'Interval': interval,
            'TTL': ttl
        })
        return Response.create_from_http_response(response)

    def deregister(self, check_id):
        response = self.put_response(url_parts=['deregister', check_id])
        return Response.create_from_http_response(response)

    def ttl_pass(self, check_id):
        response = self.put_response(url_parts=['pass', check_id])
        return Response.create_from_http_response(response)

    def ttl_warn(self, check_id):
        response = self.put_response(url_parts=['warn', check_id])
        return Response.create_from_http_response(response)

    def ttl_fail(self, check_id):
        response = self.put_response(url_parts=['fail', check_id])
        return Response.create_from_http_response(response)
