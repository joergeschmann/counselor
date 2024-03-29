import logging
import os
import signal
import time
import unittest
from datetime import timedelta
from threading import Event

from counselor.sys_signals import SignalHandler
from counselor.trigger import Trigger
from counselor.watcher import Task

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class LoggerTask(Task):
    def __init__(self, name: str, interval=timedelta(seconds=1), stop_event=Event()):
        super().__init__(name=name, interval=interval, stop_event=stop_event, log_interval_seconds=2)

    def check(self):
        self.log_with_interval("{}s task's current time : {}".format(self.interval.total_seconds(), time.ctime()))


class TriggerTests(unittest.TestCase):
    def test_triggers(self):
        trigger = Trigger()

        stop_event = Event()
        two_sec_task = LoggerTask("2s", timedelta(seconds=2), stop_event)
        trigger.add_task(two_sec_task)

        three_sec_task = LoggerTask("3s", timedelta(seconds=3), stop_event)
        trigger.add_task(three_sec_task)

        trigger.run()

        close_event = Event()
        signal_handler = SignalHandler(close_event)
        signal.signal(signal.SIGTERM, signal_handler.handle)

        close_event.wait(7)
        os.kill(os.getpid(), signal.SIGTERM)
        close_event.wait(1)

        trigger.stop_tasks()


if __name__ == '__main__':
    unittest.main()
