import threading
import queue
import itertools
import time
from typing import List, Optional, Tuple, Any


class Partition:
    """A single partition representing an append-only log of messages.

    Messages are stored as (offset, payload) pairs. Offsets are assigned
    monotonically increasing integers starting from 0.

    Thread safety:
        - All writes and reads are protected by a lock.
        - The internal queue is used as a backing store but we manually
          peek into its underlying deque to support offset-based reads.
    """

    def __init__(self) -> None:
        """Initialize an empty partition."""
        self.q: "queue.Queue[Tuple[int, Any]]" = queue.Queue()
        self.lock = threading.Lock()
        self.offset: int = 0  # next global offset to assign in this partition

    def put(self, message: Any) -> None:
        """Append a new message to the partition.

        Args:
            message: The message payload to store.
        """
        with self.lock:
            self.q.put((self.offset, message))
            self.offset += 1

    def get(self, consumer_offset: int) -> Optional[Tuple[int, Any]]:
        """Fetch the next message at or after the given consumer offset.

        This does not remove the message from the partition; it simply
        returns the first message whose offset is >= consumer_offset.

        Args:
            consumer_offset: The offset from which the consumer wants
                to start reading.

        Returns:
            A tuple (offset, message) if a matching message exists,
            otherwise None when there is no new message.
        """
        with self.lock:
            if self.q.empty():
                return None

            # Peek at all messages and find the first with offset >= consumer_offset
            items = list(self.q.queue)
            for offset, msg in items:
                if offset >= consumer_offset:
                    return offset, msg

            return None


class Broker:
    """Broker that manages multiple partitions and routes messages.

    The broker:
      - Holds a fixed number of Partition instances.
      - Assigns messages to partitions using round-robin.
      - Serves read requests for a specific partition and consumer offset.
    """

    def __init__(self, partition_count: int = 3) -> None:
        """Initialize the broker with a given number of partitions.

        Args:
            partition_count: Number of partitions to create and manage.
        """
        self.partitions: List[Partition] = [Partition() for _ in range(partition_count)]
        # Round-robin generator over partition indices
        self.counter = itertools.cycle(range(partition_count))

    def send_message(self, message: Any) -> int:
        """Send a message to the broker and assign it to a partition.

        Messages are distributed in round-robin fashion across partitions.

        Args:
            message: The message payload to send.

        Returns:
            The index of the partition the message was assigned to.
        """
        partition_index = next(self.counter)
        partition = self.partitions[partition_index]
        partition.put(message)
        return partition_index

    def receive_message(self, partition_index: int, consumer_offset: int) -> Optional[Tuple[int, Any]]:
        """Fetch the next message from a specific partition for a consumer.

        Args:
            partition_index: Index of the partition to read from.
            consumer_offset: The consumer's current offset for this partition.

        Returns:
            A tuple (offset, message) if a new message is available,
            otherwise None.
        """
        partition = self.partitions[partition_index]
        return partition.get(consumer_offset)


class Producer:
    """Producer that sends messages to the broker."""

    def __init__(self, broker: Broker) -> None:
        """Initialize the producer.

        Args:
            broker: The broker instance to which this producer will send messages.
        """
        self.broker = broker

    def send(self, message: Any) -> int:
        """Send a message via the broker.

        Args:
            message: The message payload to send.

        Returns:
            The partition index that the message was routed to.
        """
        return self.broker.send_message(message)


class Consumer:
    """Consumer that reads messages from a single partition.

    The consumer maintains its own offset per partition, representing
    the position of the *next* message to read.
    """

    def __init__(self, broker: Broker, partition_index: int) -> None:
        """Initialize a consumer bound to a specific partition.

        Args:
            broker: The broker instance to read messages from.
            partition_index: Index of the partition this consumer will read.
        """
        self.broker = broker
        self.partition_index = partition_index
        self.offset: int = 0  # next offset to read from this partition

    def poll(self) -> Optional[Any]:
        """Poll the next available message from the assigned partition.

        Returns:
            The next message payload if available, otherwise None.

        Side effects:
            - Advances the consumer's offset when a message is read.
        """
        result = self.broker.receive_message(self.partition_index, self.offset)
        if result is None:
            return None

        offset, msg = result
        # Move offset to the next unread position
        self.offset = offset + 1
        return msg


# --- Usage Example (Not distributed, but simulates the logic) ---
if __name__ == "__main__":
    # Create a broker with two partitions
    broker = Broker(partition_count=2)
    producer = Producer(broker)

    # One consumer per partition
    consumer_a = Consumer(broker, partition_index=0)
    consumer_b = Consumer(broker, partition_index=1)

    # Send messages
    for i in range(6):
        partition_index = producer.send(f"message-{i}")
        print(f"Produced message-{i} -> partition {partition_index}")

    print("\nConsumer reads:")
    # Each consumer polls its own partition
    for _ in range(3):
        msg_a = consumer_a.poll()
        msg_b = consumer_b.poll()
        print("Consumer A got:", msg_a)
        print("Consumer B got:", msg_b)
        time.sleep(0.5)