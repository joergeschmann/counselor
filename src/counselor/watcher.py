import logging
import time
from datetime import timedelta
from threading import Event, Thread

LOGGER = logging.getLogger(__name__)


class Task(Thread):
    """Base class to represent a Task that is executed by a trigger.
    """

    def __init__(self, name: str, interval: timedelta, stop_event: Event, log_interval_seconds=3 * 60 * 60,
                 daemon=True):
        Thread.__init__(self, daemon=daemon)
        self.interval = interval
        self.stop_event = stop_event
        self.name = name
        self.last_log_time = 0
        self.info_log_interval_seconds = log_interval_seconds

    def log_with_interval(self, message):
        current_timestamp = int(time.time())
        if (current_timestamp - self.last_log_time) > self.info_log_interval_seconds:
            LOGGER.info(message)
            self.last_log_time = current_timestamp

    def get_name(self):
        """Return a unique name to identify the task
        """
        return self.name

    def check(self):
        """Method to implement the check that is periodically executed
        """
        pass

    def stop(self):
        self.stop_event.set()
        self.join()

    def run(self):
        while not self.stop_event.wait(self.interval.total_seconds()):
            self.check()
