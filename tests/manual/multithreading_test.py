import logging
import random
import string
import threading
import time
import unittest
from queue import Queue

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class Item:
    def __init__(self, value: str):
        self.value = value


class Producer:
    def __init__(self):
        self._letters = string.ascii_letters
        self._value_length = 16

    def create_item(self):
        value = ''.join(random.choice(self._letters) for i in range(self._value_length))
        return Item(value)

    def produce(self):
        pass


class QueueProducer(Producer):
    def __init__(self, queue: Queue):
        super().__init__()
        self._queue = queue

    def produce(self):
        item = self.create_item()
        self._queue.put(item)
        LOGGER.info("item produced: {}".format(item.value))


class EventProducer(Producer):
    def __init__(self, event: threading.Event):
        super().__init__()
        self._event = event

    def produce(self):
        if self._event.is_set():
            LOGGER.info("last event is not consumed yet")
            return

        item = self.create_item()
        self._event.__dict__.setdefault("data", item)
        self._event.set()
        LOGGER.info("item produced: {}".format(item.value))


class ProducerThread(threading.Thread):
    def __init__(self, producer: Producer, barrier: threading.Barrier):
        threading.Thread.__init__(self, daemon=True)
        self.producer = producer
        self.interrupted = False
        self.barrier = barrier

    def run(self) -> None:
        while not self.interrupted:
            time.sleep(1)
            self.producer.produce()

        self.barrier.wait()


class Consumer:
    def __init__(self):
        self._interrupted = False

    def is_interruped(self):
        return self._interrupted

    def consume(self):
        pass


class QueueConsumer(Consumer):
    def __init__(self, queue: Queue):
        super().__init__()
        self._queue = queue
        self._draining = False

    def drain(self):
        self._draining = True

    def consume(self):
        if self._draining and self._queue.empty():
            LOGGER.info("draining done - interrupting myself")
            self._interrupted = True
            return

        item = self._queue.get()
        LOGGER.info("item consumed: {}".format(item.value))


class EventConsumer(Consumer):
    def __init__(self, event: threading.Event):
        super().__init__()
        self._event = event

    def consume(self):
        self._event.wait()
        item = self._event.__dict__.get("data")
        LOGGER.info("consumed item: {}".format(item.value))
        self._event.clear()


class ConsumerThread(threading.Thread):
    def __init__(self, consumer: Consumer, barrier: threading.Barrier):
        threading.Thread.__init__(self, daemon=True)
        self.consumer = consumer
        self.interrupted = False
        self.barrier = barrier

    def run(self) -> None:
        while not self.interrupted:
            time.sleep(random.randint(1, 3))
            self.consumer.consume()
            if self.consumer.is_interruped():
                self.interrupted = True

        self.barrier.wait()


class MultithreadingTests(unittest.TestCase):

    def test_queue_producer_consumer(self):
        queue = Queue()
        barrier = threading.Barrier(3)

        producer = QueueProducer(queue)
        producer_thread = ProducerThread(producer, barrier)
        producer_thread.start()

        consumer = QueueConsumer(queue)
        consumer_thread = ConsumerThread(consumer, barrier)
        consumer_thread.start()

        time.sleep(5)

        producer_thread.interrupted = True
        consumer.drain()

        barrier.wait()
        LOGGER.info("Finish")

    def test_event_producer_consumer(self):
        event = threading.Event()
        barrier = threading.Barrier(3)

        producer = EventProducer(event)
        producer_thread = ProducerThread(producer, barrier)
        producer_thread.start()

        consumer = EventConsumer(event)
        consumer_thread = ConsumerThread(consumer, barrier)
        consumer_thread.start()

        time.sleep(10)

        producer_thread.interrupted = True
        consumer_thread.interrupted = True

        barrier.wait()
        LOGGER.info("Finish")


if __name__ == '__main__':
    unittest.main()
