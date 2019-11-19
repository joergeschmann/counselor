import logging
import signal
import time
import unittest
from datetime import timedelta
from threading import Event

from src.counselor.signal import SignalHandler
from src.counselor.trigger import Trigger

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestTrigger(unittest.TestCase):
    def test_triggers(self):
        trigger = Trigger()

        def test_2s_func():
            print("2s task's current time : {}".format(time.ctime()))

        trigger.add_task("2s Task", func=test_2s_func, interval=timedelta(seconds=2))

        def test_3s_func():
            print("3s task's current time : {}".format(time.ctime()))

        trigger.add_task("3s Task", func=test_3s_func, interval=timedelta(seconds=3))

        trigger.run()

        close_event = Event()
        signal_handler = SignalHandler(close_event)

        close_event.wait(7)
        signal_handler.handle(signal.SIGKILL.value, None)
        close_event.wait(1)

        trigger.stop_tasks()


if __name__ == '__main__':
    unittest.main()
