from .endpoint.common import Response


class KVConfigPath:
    def __init__(self, project: str, feature: str, service: str, detail: str = "config", env: str = "dev"):
        self.project = project
        self.feature = feature
        self.service = service
        self.detail = detail
        self.env = env

    def compose_path(self) -> str:
        return "{}/{}/{}/{}/{}".format(self.project, self.env, self.feature, self.service, self.detail)


class ReconfigurableService:
    """Interface for a service to be notified by the watcher.
    Extend this class to encapsulate all the logic to reconfigure your service.
    """

    def __init__(self, service_key: str, config_path: KVConfigPath, current_config: dict):
        if service_key == "":
            raise ValueError("Please define a unique service key")
        if config_path is None:
            raise ValueError("Please define a key value path for the service config")

        # TODO: url encode the values to be safe because it will be part of the request url

        self.service_key = service_key
        self.config_path = config_path
        self.current_config = current_config

    def notify_failed_service_check(self, response: Response):
        """If the service fails to fetch the ServiceDefinition from Consul, this method is called.
        """
        pass

    def configure(self, config=dict) -> bool:
        """This method will be called when the config is fetched from Consul outside of a watcher,
        like for the initial configuration.
        """
        pass

    def reconfigure(self, new_config=dict) -> bool:
        """If the Watcher notices a change, this method is called to give the new configuration.
        """
        pass
