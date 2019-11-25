# Counselor
This lib provides functionality to interact with Consul from HashiCorp. 

It is still in work and you should not use it in production.

The main use case for this lib is, you have a service that you want to register in Consul and automatically 
reconfigure when the configuration for that service changed. Instead of having a local Consul agent running that 
executes a shell script or calls an http endpoint, Counselor uses an interface your service can implement, 
to notify it of changes to the service. The configuration of the service is stored in the KV store of Consul. 
To check for updates, a trigger periodically fetches the service definition and check it for changes.

## Setup
You can use the Makefile to install the lib locally
```ignorelang
make install
```

## Installation
Install from the test pypi repository:
```ignorelang
python -m pip install --index-url https://test.pypi.org/simple/ counselor
```

Install from the productive pypi repository, you can install it from there:
```ignorelang
python -m pip install counselor
```

## Usage
Here are some examples executed in the python console to show you how to use the library.

### KV Store
```python
import logging

from counselor.config import KVConfigPath
from counselor.discovery import ServiceDiscovery
from counselor.endpoint.http_endpoint import EndpointConfig

logging.basicConfig(level=logging.DEBUG)

# Create a ServiceDiscovery instance to interact with consul
consul_config = EndpointConfig(host="127.0.0.1", port=8500, version="v1")
service_discovery = ServiceDiscovery.new_service_discovery_with_consul_config(consul_config)

# Create a key value config path
kv_config_path = KVConfigPath("test-project", "test-domain", "test-service", "test-config", "test-env")
config_path = kv_config_path.compose_path()

# Check whether there is already a config stored in that config path.
# You get two objects back, one for the response, that lets you know whether the request was successul of not.
# The other is the config itself. If the response is successful, the config instance is filled.
response, found_config = service_discovery.fetch_config_by_path(kv_config_path.compose_path())
response.as_string()

# Create a config for your service
test_service_config = {
    "foo": "bar",
    "number": 3.1415,
    "active": True,
    "list": ["one", "two", "three"],
    "map": {"a": 1, "b": 2, "c": 3}
}

# Store the config in the Consul KV store
response = service_discovery.store_config(config_path, test_service_config)
response.as_string()

# Now you should find the config
response, found_config = service_discovery.fetch_config_by_path(config_path)
response.as_string()
found_config

# To update the config, change the config and send it to Consul. Keep in mind that the  
# config will be overwritten. That means any field that is not in the config anymore will be deleted in the KV store.
test_service_config["active"] = False
response = service_discovery.update_config(config_path, test_service_config)
response.as_string()
```

### Service registry
```python
from counselor.discovery import ServiceDiscovery
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.filter import KeyValuePair


# Create a ServiceDiscovery instance to interact with consul
consul_config = EndpointConfig(host="127.0.0.1", port=8500, version="v1")
service_discovery = ServiceDiscovery.new_service_discovery_with_consul_config(consul_config)

# To register a service you need at least a unique key. This key is used to identify your service. Consul has only
# this level of identification. So if you track multiple instance of the same service, you might add a number to 
# differentiate between the instances.
service_key = "test-service"

# You can group your service with tags. For example, you could tag all your db services with the tag "db".
# A dash in the tag name can cause errors. You should use an underscore _ instead.
service_tags = ["test"]

# The meta field allows you to define arbitrary characteristics of your service. In this example we have the version,
# the status and the base_time stored. The only limitation is that all keys and values have to be strings.
service_meta = {
    "version": "1.0",
    "status": "active",
    "base_time": "1573639530",
}

# Register the service 
response = service_discovery.register_service(service_key=service_key, tags=service_tags, meta=service_meta)
response.as_string()

# Fetch the service definition.
response, found_service = service_discovery.get_service_details(service_key)
response.as_string()
found_service.as_json()

# To update the service modify the tag or meta field and send it to Consul.
service_tags = service_tags + ["additional_tag"]
service_meta = {
    "status": "inactive"
}
response = service_discovery.update_service(service_key=service_key, tags=service_tags, meta=service_meta)

# You are able to use the tags and meta map to search and filter the services.
response, found_services = service_discovery.search_for_services(tags=["additional_tag"], meta=[KeyValuePair('status', 'inactive')])
response.as_string()
found_services[0].as_json()

# At the end you can deregister your service by key
response = service_discovery.deregister_service(service_key)
response.as_string()
```

### Watch for config changes
```python
import logging
from datetime import timedelta
from threading import Event

from counselor.config import KVConfigPath
from counselor.discovery import ServiceDiscovery
from counselor.endpoint.common import Response
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.watcher import ReconfigurableService

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Create a ServiceDiscovery instance to interact with consul
consul_config = EndpointConfig(host="127.0.0.1", port=8500, version="v1")
service_discovery = ServiceDiscovery.new_service_discovery_with_consul_config(consul_config)

# To check for config updates in Consul, there is a Trigger that periodically fetches the config from Consul.
# It then compares the received config with the last know version. If there is a difference, it will notify you.
# We have an interface for that, called ReconfigurableService. You have to extend that class to provide the 
# necessary functionality. In the followed example, the TestService simply logs the events.
#
# notify_failed_service_check() is called when Consul is not reachable or does not return the config.
# configure() is called the first time it fetches the config
# reconfigure() is called whenever the modification_index is increased and an update available
class TestService(ReconfigurableService):
    def __init__(self, service_key: str, config_path: KVConfigPath, current_config: dict = None):
        self.service_key = service_key
        self.config_path = config_path
        self.last_config = current_config
        self.failed_service_check = False
        self.updated = False

    def get_service_key(self) -> str:
        return self.service_key

    def get_current_config(self) -> dict:
        return self.last_config

    def get_config_path(self) -> str:
        return self.config_path.compose_path()

    def notify_failed_service_check(self, response: Response):
        LOGGER.info("Failed service check: {}".format(response.as_string()))
        self.failed_service_check = True

    def configure(self, config=dict) -> bool:
        LOGGER.info("Configured: {}".format(config))
        self.last_config = config
        self.failed_service_check = False
        return True

    def reconfigure(self, new_config=dict) -> bool:
        LOGGER.info("New configuration received: {}".format(new_config))
        self.configure(new_config)
        self.updated = True
        return True

# Create an instance of your service facade, that lets the watcher notify your service of changes
test_service = TestService(service_key="test-service",
    config_path=KVConfigPath("test", "feature", "service", "config", "env"), 
    current_config={
        "foo": "bar",
        "number": 3.1415,
        "active": True,
        "list": ["one", "two", "three"],
        "map": {"a": 1, "b": 2, "c": 3}
    })

# The service definition and the config in the KV store are seperate. You can store a config and watch for updates, 
# without having the service registered. The method register_service_and_store_config will do both in one call.
service_tags = ["test"]
service_meta = None
response = service_discovery.register_service_and_store_config(reconfigurable_service=test_service, tags=service_tags,
    meta=service_meta)
response.as_string()

# You can add one or multiple config watches and start the trigger.
# With the stop you have the ability to stop the watcher by setting the event. This is helpful if you have other
# resources and you want to have a graceful shut down. 
stop_event = Event()
service_discovery.add_config_watch(service=test_service, check_interval=timedelta(seconds=3), stop_event=stop_event)
response = service_discovery.start_config_watch()

# Once the watcher is started, you should see log messages that Consul is checked for updates.
# You can now either change the service either via Consul UI or with the service_discovery instance.
test_service.last_config["reconfigure_action"] = "reload"
response = service_discovery.update_config_by_service(test_service)

# You should then see that a new config is recieved and the update flag is set.
test_service.updated

# To stop the watcher you can either set the event,
stop_event.set()
# stop the trigger directly,
service_discovery.stop_config_watch()
# or clear the watchers
service_discovery.clear_watchers()
``` 

For other examples, please have a look at the test folder.

