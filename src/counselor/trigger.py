import logging
from datetime import timedelta
from threading import Thread, Event

LOGGER = logging.getLogger(__name__)


class Task(Thread):
    """Base class to represent a Task that is executed by a trigger.
    """

    def __init__(self, name: str, interval: timedelta, execute, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self.name = name
        self.stopped = Event()
        self.interval = interval
        self.execute = execute

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.wait(self.interval.total_seconds()):
            self.execute()


class Trigger(Thread):
    """Periodically execute registered tasks.
    """

    def __init__(self):
        Thread.__init__(self)
        self.tasks = []

    def add_task(self, name: str, func, interval: timedelta, *args, **kwargs):
        t = Task(name, interval, func, *args, **kwargs)
        self.tasks.append(t)

    def run(self):
        LOGGER.info("Starting tasks...")

        for t in self.tasks:
            t.start()
            LOGGER.info("Active task {}".format(t.name))

        LOGGER.info("Trigger is active.")

    def stop_tasks(self):
        for t in self.tasks:
            LOGGER.info("Stopping task {}".format(t.name))
            t.stop()

        LOGGER.info("Trigger exited.")
