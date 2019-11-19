import logging

from .endpoint import Endpoint

LOGGER = logging.getLogger(__name__)


class KV(Endpoint):
    """Key value store interface to consul.

        TODO: use StatusResponse as returned value
    """

    def get(self, item, default=None, raw=False):
        """Get a value.
        """

        response = self._get_item(item, raw)
        if isinstance(response, dict):
            return response.get('Value', default)

        return response or default

    def set(self, item, value):
        """Set a value.
        """

        return self._set_item(item, value)

    def delete(self, item, recurse=False):
        """Remove an item.
        """

        query_params = {'recurse': True} if recurse else {}
        return self._transport.delete(self._build_uri([item], query_params))

    def acquire_lock(self, item, session):
        """Set a lock.
        """

        return self._put_response([item], {'acquire': session})

    def release_lock(self, item, session):
        """Release a lock.
        """
        return self._put_response([item], {'release': session})

    def _get_item(self, item, raw=False):
        """Get an item from Consul.
        """

        item = item.lstrip('/')
        query_params = {'raw': True} if raw else {}
        response = self._transport.get(self._build_uri([item], query_params))

        if not response.is_successful():
            LOGGER.warning("Could not get KV: {}".format(response.as_string()))
            return None
        else:
            return response.payload

    def _set_item(self, item, value, flags=None):
        """Set an item in Consul.
        """

        if item and item.endswith('/'):
            item = item.rstrip('/')

        query_params = {}
        if flags is not None:
            query_params['flags'] = flags

        response = self._transport.put(self._build_uri([item], query_params), value)

        if not response.is_successful():
            LOGGER.warning("Could not set KV: {}".format(response.as_string()))
            return None
        else:
            return response.payload
