# Distributed Message Queue (Python Example)

A minimal in-memory **distributed-style message queue** implemented in Python.

This project models the core components of a distributed message queue system,
inspired by designs from systems like Kafka and by  
_System Design Interview – Volume 2, Chapter 4 (Alex Xu)_.

It is intended for **learning and experimentation**, not production use.

---

## Overview

This project simulates the key building blocks of a distributed message queue:

- **Partition**  
  Append-only log of messages, each with a monotonically increasing offset.

- **Broker**  
  Manages multiple partitions and routes messages to them (round-robin).

- **Producer**  
  Sends messages to the broker, which assigns them to partitions.

- **Consumer**  
  Reads from a single partition and tracks its own offset (next position to read).

All components run in a single process and fully in-memory, but the design
captures essential concepts such as partitions, offsets, producers, and consumers.

---

## Architecture Overview

High-level flow:

```text
Producer ───► Broker ───► Consumers
```

The Broker contains multiple **partitions**, each acting as an ordered log:

```text
             ┌──────────── Broker ─────────────┐
             │                                 │
             │   ┌────────────┐  ┌────────────┐│
Producer ───►│   │ Partition0 │  │ Partition1 ││ ───► Consumers
             │   └────────────┘  └────────────┘│
             └─────────────────────────────────┘
```

---

## Partition Structure

Each message is stored with an **offset**, increasing monotonically.

Example after producing 6 messages:

```text
Partition 0:           Partition 1:
[0:msg0]               [0:msg1]
[1:msg2]               [1:msg3]
[2:msg4]               [2:msg5]
```

Partitions behave like append-only logs:

```text
offset →  0     1     2
        ┌─────┬─────┬─────┐
        │  A  │  C  │  E  │   (Partition 0)
        └─────┴─────┴─────┘
```

---

## Consumer Offsets

Each consumer tracks its **own reading position**:

```text
Consumer A reading Partition 0:
  offset=0 → read msg0 → next offset=1
  offset=1 → read msg2 → next offset=2
  offset=2 → read msg4 → next offset=3
```

Consumers do not interfere with each other and never block one another.

Visual:

```text
Partition 0: [0:msg0][1:msg2][2:msg4]
Consumer A offset → 3   (next unread message)
```

---

## Code Structure

```text
project/
│
├── queue.py    # Broker, Partition, Producer, Consumer, and usage example
└── README.md
```

---

## Running the Example

```bash
python queue.py
```

Sample output:

```text
Produced message-0 -> partition 0
Produced message-1 -> partition 1
Produced message-2 -> partition 0
Produced message-3 -> partition 1
Produced message-4 -> partition 0
Produced message-5 -> partition 1

Consumer reads:
Consumer A got: message-0
Consumer B got: message-1
Consumer A got: message-2
Consumer B got: message-3
Consumer A got: message-4
Consumer B got: message-5
```

---

## Testing

### Unit Tests

Create `test_queue.py`:

```python
import unittest
from queue import Broker, Producer, Consumer

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
```

Run tests:

```bash
python -m unittest test_queue.py
```

---

## Key Concepts Demonstrated

1. **Partitioned Logs**
   Each partition is an ordered append-only message log.

2. **Consumer Offsets**
   Consumers track their own progress so:

   - they read independently
   - they can replay messages
   - they never block one another

3. **Round-robin Load Balancing**
   Producer distributes load across partitions.

4. **Thread Safety**
   Locks simulate concurrency safety inside each partition.

---

## Future Extensions

You can extend this project with:

- Persistent log segments (Kafka-style)
- Consumer groups
- Replication across multiple brokers
- Networked producers/consumers using sockets or gRPC
- Retention policies and log compaction

---

## License

MIT License
