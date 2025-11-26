# Minimal Chat System (Python, Sockets)

A tiny low-level chat system written in pure Python using TCP sockets and threads.  
This repo contains:

- `chat_server.py` – multi-client chat server
- `chat_client.py` – terminal client

It’s intentionally simple to match “system design a chat app” concepts with real code.

---

## Features

- Multiple clients connected at once
- Simple text protocol over TCP
- Chat rooms (1-1 or group style)
- Join / leave rooms
- Broadcast messages to everyone in a room

No frameworks, no databases, no external deps.

---

## Requirements

- Python 3.8+
- Works on Linux, macOS, and Windows

No extra packages needed beyond the standard library.

---

## Getting Started

Clone the repo:

```bash
git clone https://github.com/<your-username>/minimal-chat-system.git
cd minimal-chat-system
```

### 1. Run the server

```bash
python chat_server.py
```

The server listens on `0.0.0.0:5000` by default.
Edit `HOST` / `PORT` in `chat_server.py` if you want to change it.

### 2. Run a client

In a **new** terminal:

```bash
python chat_client.py
```

You’ll be asked for:

- `username`
- `room` (e.g. `lobby`)

Open more terminals and run more clients to simulate multiple users.

---

## Client Commands

Inside the client:

- Send a message to the current room:
  Just type and hit Enter.
- Join another room:

  ```text
  /join room-name
  ```

- Leave a room:

  ```text
  /leave room-name
  ```

- Quit the client:

  ```text
  /quit
  ```

---

## Text Protocol (Server API)

The client and server use a very simple line-based protocol:

**Commands from client → server**

- `JOIN <room> <username>`
- `MSG <room> <text...>`
- `LEAVE <room>`
- `QUIT`

**Messages from server → client**

- Informational:

  - `INFO some text...`

- Chat messages:

  - `MSG <room> <username> <text...>`

- Errors:

  - `ERROR description`

You can even test the server with `nc` / `telnet`:

```bash
nc 127.0.0.1 5000
JOIN lobby alice
MSG lobby hello from netcat
```

---

## How This Maps to System Design

This project is deliberately minimal, but corresponds to bigger system-design pieces:

- In-memory `rooms` dict → would become Redis / DB in a real system
- One process with threads → would become many chat servers behind a load balancer
- Simple text protocol → would become a structured WebSocket/HTTP API
- No persistence → would become a message store (PostgreSQL, Cassandra, etc.)

---

## License

MIT
