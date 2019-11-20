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

from counselor.watcher import ReconfigurableService
from counselor.discovery import ServiceDiscovery

from datetime import timedelta

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Define a service that get automatically reconfigured 
# -> this is where you can encapsulate all the functionality to reconfigure/reload your service
class TestService(ReconfigurableService):
    def __init__(self):
        super().__init__()
        self.last_config = None
        self.failed_service_check = False
    def notify_failed_service_check(self):
        LOGGER.info("Failed service check")
        self.failed_service_check = True
    def reconfigure(self, new_config=dict) -> bool:
        LOGGER.info("New configuration received: {}".format(new_config))
        self.last_config = new_config
        self.failed_service_check = False
        return True

# Create a ServiceDiscovery instance to interact with consul
service_discovery = ServiceDiscovery.new_service_discovery_with_default_consul_client()

# Register a service in Consul
register_status = service_discovery.register_service(service_key="my-test-service", tags=["test"], meta={
    "version": "1.0",
    "status": "active",
    "base_time": "1573639530",
})

# Print the response
register_status.as_string()

# Create an instance of your service facade, that lets the watcher notify your service of changes
test_service = TestService()

# Start the watcher with an interval of 3 seconds -> you should see log messages that the watcher is active
watch_status = service_discovery.start_config_watch(test_service, timedelta(seconds=3))

# Print the repsonse
watch_status.as_string()

# Change the configuration
service_discovery.service_definition.meta["addition"] = "True"

# Update the service definition -> you should see a log message that your service received a new config
update_status = service_discovery.update_service_definition()

# Print the response
update_status.as_string()

# Your service instance should contain the new config
test_service.last_config

# Stop the watcher
service_discovery.stop_config_watch()

# Deregister the service
deregister_status = service_discovery.deregister_service()

# Print the resopnse
deregister_status.as_string()

# You should not have any registered services left
response, services = service_discovery.consul.agent.services()
response.as_string()
services
```

For other examples, please have a look at the test folder.

