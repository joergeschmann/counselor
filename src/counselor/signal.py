import logging
import signal
from threading import Event

LOGGER = logging.getLogger(__name__)


class SignalHandler:
    """Signal handler to implement graceful shutdowns.
    """

    def __init__(self, parent_event: Event):
        self.parent_event = parent_event
        self.signals = [signal.SIGHUP, signal.SIGINT, signal.SIGTERM]
        for sig in self.signals:
            signal.signal(sig, self.handle)

    def handle(self, signum, frame):
        LOGGER.info("Signal received: {}".format(signal.Signals(signum).name))
        self.parent_event.set()
