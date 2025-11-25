import unittest
from distributed_message_queue import Broker, Producer, Consumer

class TestMessageQueue(unittest.TestCase):

    def test_round_robin_distribution(self):
        broker = Broker(partition_count=2)
        producer = Producer(broker)

        partitions = [producer.send(f"m{i}") for i in range(4)]
        self.assertEqual(partitions, [0, 1, 0, 1])

    def test_consumer_reads_in_order(self):
        broker = Broker(partition_count=1)
        producer = Producer(broker)
        consumer = Consumer(broker, partition_index=0)

        producer.send("a")
        producer.send("b")
        producer.send("c")

        self.assertEqual(consumer.poll(), "a")
        self.assertEqual(consumer.poll(), "b")
        self.assertEqual(consumer.poll(), "c")
        self.assertIsNone(consumer.poll())

    def test_independent_offsets(self):
        broker = Broker(partition_count=1)
        producer = Producer(broker)

        c1 = Consumer(broker, 0)
        c2 = Consumer(broker, 0)

        producer.send("x")
        producer.send("y")

        self.assertEqual(c1.poll(), "x")
        self.assertEqual(c1.poll(), "y")

        # c2 has its own offset; it replays from the beginning
        self.assertEqual(c2.poll(), "x")

if __name__ == "__main__":
    unittest.main()
