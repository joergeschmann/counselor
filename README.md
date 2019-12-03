# Counselor
This lib provides functionality to interact with Consul from HashiCorp. 

It is still in work and you should not use it in production.

The main use case for this lib is, you have a service that you want to register in Consul and automatically 
reconfigure when the configuration changed for that service. Instead of having a local Consul agent running that 
executes a shell script or calls an http endpoint, Counselor uses an interface your service can implement, 
to notify it of changes to the service. The configuration of the service is stored in the KV store of Consul. 
To check for updates, a trigger periodically fetches the service definition and check it for changes.

## Setup
You can use the Makefile to install the lib locally
```ignorelang
make install
```

## Installation
Local installation via Makefile:
```ignorelang
make install
```
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

### ServiceDiscovery class
The simplest way is to use the ServiceDiscovery class which acts as a facade.
```python
import logging
from counselor import client
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.discovery import ServiceDiscovery

logging.basicConfig(level=logging.DEBUG)

# Create a ServiceDiscovery instance to interact with Consul. If you have ACL enabled, you can add your token to the EndpointConfig.
consul_config = EndpointConfig(host="127.0.0.1", port=8500, version="v1", token="")
consul_client = client.ConsulClient(config=consul_config)
service_discovery = ServiceDiscovery.new_service_discovery_with_consul_client(consul_client)

# With the service_discovery instance you are able to interact with Consul easily.
```

### KV Store
```python
import logging

from counselor.discovery import ServiceDiscovery
from counselor.endpoint.kv_endpoint import KVPath

logging.basicConfig(level=logging.DEBUG)

# Create a ServiceDiscovery instance with the default config values.
service_discovery = ServiceDiscovery.new_service_discovery_with_defaults()

# Create a key value config path to define where to store the config.
kv_config_path = KVPath("test-project", "test-domain", "test-service", "test-config", "test-env")

# The entire path then be composed viaservice_discovery = ServiceDiscovery.new_service_discovery_with_consul_client(consul_client) its method.
config_path = kv_config_path.compose_path()

# Check whether there is already a config stored in that config path.
# You get two objects back, one for the response, that lets you know whether the request was successful or not.
# The other is the config itself. If the response is successful, the config instance is filled.
response, found_config = service_discovery.fetch_config_by_path(config_path)
response.as_string()

# Create a config for your service.
test_service_config = {
    "foo": "bar",
    "number": 3.1415,
    "active": True,
    "list": ["one", "two", "three"],
    "map": {"a": 1, "b": 2, "c": 3}
}

# Store the config in the Consul KV store.
response = service_discovery.store_config(config_path, test_service_config)
response.as_string()

# Now you should find the config.
response, found_config = service_discovery.fetch_config_by_path(config_path)
response.as_string()
found_config

# To update the config, change the config and send it to Consul. Keep in mind that the  
# config will be overwritten. That means any field that is not in the config anymore will be deleted in the KV store.
test_service_config["active"] = False
response = service_discovery.update_config(config_path, test_service_config)
response.as_string()

# If you want to only update a single field, you can use the merge method.
response = service_discovery.merge_config(config_path, {"single-field": "that is added to the existing config"})
response.as_string()

# There is also a method to fetch a config path recursively and get and array. 
response, found_configs = service_discovery.fetch_config_recursively(config_path)
found_configs

# To clean up, we can also delete entries.
response = service_discovery.delete_config(path=config_path, recurse=True)
```

### Service registry
```python
import logging 

from counselor.discovery import ServiceDiscovery
from counselor.endpoint.entity import ServiceDefinition
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.filter import KeyValuePair

logging.basicConfig(level=logging.DEBUG)

# Create a ServiceDiscovery instance to interact with consul.
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

# The ServiceDefinition class holds all those details.
service_definition = ServiceDefinition(
    key=service_key,
    tags=service_tags,
    meta=service_meta
)


# Register the service 
response = service_discovery.register_service(service_definition)
response.as_string()

# Fetch the service definition.
response, found_service = service_discovery.get_service_details(service_key)
response.as_string()
found_service.as_json()

# To update the service modify the tag or meta field and send it to Consul.
service_definition.tags.append("additional_tag")
service_definition.meta["status"] = "inactive"
response = service_discovery.update_service(service_definition)

# You are able to use the tags and meta map to search and filter the services.
response, found_services = service_discovery.search_for_services(tags=["additional_tag"], meta=[KeyValuePair('status', 'inactive')])
response.as_string()
found_services[0].as_json()

# At the end you can deregister your service by key.
response = service_discovery.deregister_service(service_key)
response.as_string()
```

### Watch for config changes
```python
import logging
from datetime import timedelta
from threading import Event

from counselor.discovery import ServiceDiscovery, ReconfigurableService
from counselor.endpoint.http_endpoint import EndpointConfig
from counselor.endpoint.kv_endpoint import KVPath
from counselor.kv_watcher import ConfigUpdateListener

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Create a ServiceDiscovery instance to interact with consul.
consul_config = EndpointConfig(host="127.0.0.1", port=8500, version="v1")
service_discovery = ServiceDiscovery.new_service_discovery_with_consul_config(consul_config)

# Create a key value config path to define where to store the config.
kv_config_path = KVPath("test-project", "test-domain", "test-service", "test-config", "test-env")

# Create a config
current_config={
        "foo": "bar",
        "number": 3.1415,
        "active": True,
        "list": ["one", "two", "three"],
        "map": {"a": 1, "b": 2, "c": 3}
    }

# To have ereything in one place, there is the ReconfigurableService, that holds all the infos about a service.
service = ReconfigurableService(service_key="test-service", 
    config_path=kv_config_path, 
    current_config=current_config, 
    tags=["test"], 
    meta={})

# The service definition and the config in the KV store are separate. You can store a config and watch for updates, 
# without having the service registered. The method register_service_and_store_config will do both in one call.
response = service_discovery.register_service_and_store_config(service)
response.as_string()

# To check for config updates in Consul, there is a Trigger that periodically fetches the config from Consul.
# It then compares the received config with the last know version. If there is a difference, it will notify you.
# We have an interface for that, called ConfigUpdateListener. You have to extend that class to provide the 
# necessary functionality. In the following example, the TestUpdateListener simply logs the events.
#
# get_path() returns the kv path in Consul.
# on_init() is called the first time it fetches the config. 
# on_update() is called whenever the modification_index is increased and an update available. 
class TestListener(ConfigUpdateListener):
    def __init__(self, service: ReconfigurableService):
        self.service = service
        self.initialized = False
        self.updated = False

    def get_path(self) -> str:
        return self.service.compose_config_path()

    def on_init(self, config: dict) -> bool:
        for key in config.keys():
            self.service.current_config[key] = config[key]
        self.initialized = True
        LOGGER.info("Initialized {}".format(config))
        return True

    def on_update(self, new_config: dict) -> bool:
        self.service.current_config = new_config
        self.updated = True
        LOGGER.info("Updated {}".format(new_config))
        return True


# Create an instance of your listener, that lets the watcher notify your service of changes.
test_listener = TestListener(service)

# You can add one or multiple config watchers and start the trigger.
# With the stop you have the ability to stop the watcher by setting the event. This is helpful if you have other
# resources and you want to have a graceful shut down. 
check_interval=timedelta(seconds=3)
stop_event = Event()
service_discovery.add_config_watch(listener=test_listener, check_interval=check_interval, stop_event=stop_event)
response = service_discovery.start_config_watch()
# When it starts to fetch the config, it will recognize the first fetch, because there is not modify index of Consul yet.
# So it will trigger the on_init function of the listener which you should see in the logs. 

# Once the watcher is started, you should see log messages that Consul is checked for updates.
# You can now either change the service either via Consul UI, with the service_discovery instance, or via separate updater.
service_config_updater = service_discovery.create_kv_updater_for_path(service.compose_config_path())
response = service_config_updater.merge({"reload-action": "reboot"})

# You should then see that a new config is recieved and the update flag is set.
test_listener.updated

# To stop the watcher you can either set the event,
stop_event.set()
# stop the trigger directly,
service_discovery.stop_config_watch()
# or clear the watchers
service_discovery.clear_watchers()

# If not done yet, the deregister function will stop all watchers.
response = service_discovery.deregister_service(service.service_key)
``` 

For other examples, please have a look at the test folder.