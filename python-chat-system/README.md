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

There's also a tiny web UI if you prefer a browser-based chat.

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

### Optional: Run the "Mini Zoom Chat" web UI (long-polling)

```bash
python mini_zoom_chat.py --port 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your browser,
enter a username/room, and chat via the simple web interface using
long-polling requests. It defaults to port `8000` because the socket-based
`chat_server.py` already listens on `5000`.

Notes for the browser UI:

- Each room keeps only the latest 500 messages in memory to avoid unbounded
  growth if a room stays busy for a long time.
- The long-polling endpoints are served directly by `mini_zoom_chat.py`; they
  do not reuse the TCP socket protocol from `chat_server.py`.
- You can open as many **clients** as you like against the same port (multiple
  browser tabs or terminals running `chat_client.py`), but only **one server
  process** can bind to that port at a time. If you start `mini_zoom_chat.py`
  twice on `:5000`, the second process will fail with “address already in use”
  whether you’re local, in VS Code, or in Codespaces.
- If it ever looks like two shells are “both running” `mini_zoom_chat.py` on
  the same port locally, one of them either exited (e.g., after a `Ctrl+C`) or
  failed to bind and printed the port-in-use error. The active clients are all
  hitting the single process that successfully owns the port. You can confirm
  the owner with `lsof -i :8000` (macOS/Linux) if you’re unsure which shell is
  the real server.

#### Reusing port 5000 for the web UI

You can run the browser UI on `:5000`, but only **one** server can own that
port at a time. Pick one of these approaches:

1. **Switch entirely to the HTTP UI:**

   ```bash
   # stop any running chat_server.py process first
   python mini_zoom_chat.py --port 5000
   ```

   This runs the long-polling HTTP server (and its in-memory rooms) on the
   same address the TCP server normally uses.

2. **Combine everything under a single HTTP entrypoint:** refactor
   `chat_server.py` to expose HTTP endpoints (or import its room storage into
   `mini_zoom_chat.py`) and run just one HTTP server on `:5000`. Two separate
   processes cannot safely share the same port without an external proxy that
   understands both protocols, so a combined server is the simplest way to
   serve both the browser UI and chat API on one address.

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
