# Counselor
This lib provides functionality to interact with Consul from HashiCorp. 

It is still in work and you should not use it in production.

The main use case for this lib is, you have a service that you want to register in Consul and automatically reconfigure when the configuration for that service changed. Instead of having a local Consul agent running that executes a shell script or calls an http endpoint, Counselor uses an interface your service can implement, to notify it of changes to the service. The configuration of the service is stored in the meta field in Consul. To check for updates, a trigger periodically fetches the service definition and check it for changes.

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
```python
import logging
from datetime import timedelta
import uuid

from counselor.client import ConsulConfig
from counselor.config import KVConfigPath
from counselor.discovery import ServiceDiscovery
from counselor.endpoint.common import Response
from counselor.filter import KeyValuePair
from counselor.watcher import ReconfigurableService

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Define a service that get automatically reconfigured 
# -> this is where you can encapsulate all the functionality to reconfigure/reload your service
class TestService(ReconfigurableService):
    def __init__(self, service_key: str, kv_config_path: KVConfigPath, current_config: dict = None):
        super().__init__(service_key, kv_config_path, current_config)
        self.failed_service_check = False
        self.updated = False

    def notify_failed_service_check(self, response: Response):
        LOGGER.info("Failed service check: {}".format(response.as_string()))
        self.failed_service_check = True

    def configure(self, config=dict) -> bool:
        LOGGER.info("Configuring service")
        self.current_config = config
        self.failed_service_check = False
        self.updated = True
        return True

    def reconfigure(self, new_config=dict) -> bool:
        LOGGER.info("New configuration received: {}".format(new_config))
        self.configure(new_config)
        return True

# Create a ServiceDiscovery instance to interact with consul
consul_config = ConsulConfig(host="127.0.0.1", port=8500)
service_discovery = ServiceDiscovery(consul_config)

# Define the path in the KV store in Consul -> v1/kv/test/env/feature/service/config
kv_config_path = KVConfigPath("test", "feature", "service", "config", "env")

# Your current service config, that you want to store in Consul
current_config = {
    "foo": "bar",
    "number": 3.1415,
    "active": True,
    "list": ["one", "two", "three"],
    "map": {"a": 1, "b": 2, "c": 3}
}

# Create an instance of your service facade, that lets the watcher notify your service of changes
test_service = TestService(uuid.uuid4().hex, kv_config_path, current_config)

# Check whether there is already a config stored in Consul
service_discovery.fetch_config(test_service)

# If not store it -> you should see it in the UI: http://localhost:8500/ui/dc1/kv/test/env/feature/service/config/edit
config_store_response = service_discovery.store_config(test_service)
config_store_response.as_string()

# Register a service in Consul -> you should see the registered service
register_response = service_discovery.register_service(service_key=test_service.service_key, tags=["test"], meta={
    "version": "1.0",
    "status": "active",
    "base_time": "1573639530",
})
register_response.as_string()

# Start the watcher with an interval of 3 seconds -> you should see log messages that the watcher is active
interval = timedelta(seconds=3)
watch_response = service_discovery.start_config_watch(test_service, interval)
watch_response.as_string()

# Change the configuration, you can also do it via Consul ui -> you should see a log message that your service received a new config
test_service.current_config["reconfigure_action"] = "restart"
update_response = service_discovery.store_config(test_service)
update_response.as_string()

# Your service instance should have set the updated flag by now
test_service.updated

# Stop the watcher
service_discovery.stop_config_watch()

# Deregister the service
deregister_response = service_discovery.deregister_service()
deregister_response.as_string()

# You should not have any registered services left
search_response, found_services = service_discovery.search_for_services(tags=["test"],
                                                                              meta=[KeyValuePair('status', 'active')])
search_response.as_string()
found_services
```

For other examples, please have a look at the test folder.

