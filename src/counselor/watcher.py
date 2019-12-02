import logging
from datetime import timedelta
from threading import Event, Thread

LOGGER = logging.getLogger(__name__)


class Task(Thread):
    """Base class to represent a Task that is executed by a trigger.
    """

    def __init__(self, name: str, interval: timedelta, stop_event: Event, daemon=True):
        Thread.__init__(self, daemon=daemon)
        self.interval = interval
        self.stop_event = stop_event
        self.name = name

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
