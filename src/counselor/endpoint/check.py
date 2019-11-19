from .endpoint import Endpoint


class Check(Endpoint):
    """
        At the moment checks are implemented as periodic http requests with our own watcher implementation.
        The next step is to involve the consul agent.
        TODO: implement
    """

    def register(self, name, script=None, check_id=None, interval=None, ttl=None, notes=None, http=None):
        return self._put_response(url_parts=['register'], query=None, payload={
            'ID': check_id,
            'Name': name,
            'Notes': notes,
            'Script': script,
            'HTTP': http,
            'Interval': interval,
            'TTL': ttl
        }, response_parser=None)

    def deregister(self, check_id):
        return self._put_response(url_parts=['deregister', check_id], response_parser=None)

    def ttl_pass(self, check_id):
        return self._put_response(url_parts=['pass', check_id], response_parser=None)

    def ttl_warn(self, check_id):
        return self._put_response(url_parts=['warn', check_id], response_parser=None)

    def ttl_fail(self, check_id):
        return self._put_response(url_parts=['fail', check_id], response_parser=None)
