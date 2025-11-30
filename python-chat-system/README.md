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

And a FastAPI + WebSocket service that is stateless and ready for container
deployments.

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

### Optional: Run the FastAPI WebSocket + HTTP API (stateless & containerized)

This service uses FastAPI with Redis pub/sub so multiple app instances can stay
in sync without keeping per-room state in-memory, and PostgreSQL for durable
message history and metadata. It exposes:

- `POST /api/send` – publish a chat message to a room.
- `GET /health` – health check.
- `WS /ws/{room}/{username}` – WebSocket endpoint for bi-directional chat.

#### Local run (needs Redis + PostgreSQL)

Start Redis (Docker example):

```bash
docker run -p 6379:6379 --name chat-redis -d redis:7-alpine
```

Start PostgreSQL (Docker example):

```bash
docker run -p 5432:5432 --name chat-postgres -e POSTGRES_USER=chatuser -e POSTGRES_PASSWORD=chatpass -e POSTGRES_DB=chatdb -d postgres:16-alpine
```

Install deps and launch the FastAPI service (it will auto-create the
`chat_messages` table on startup):

```bash
pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379/0
export DATABASE_URL=postgresql://chatuser:chatpass@localhost:5432/chatdb
uvicorn fastapi_chat:app --host 0.0.0.0 --port 8000
```

Use the same Redis URL in all replicas (set `REDIS_URL` if different) to scale
the service horizontally behind a load balancer. In this document, a *replica*
means any independent app instance (container, process, pod, VM, etc.) running
`fastapi_chat.py` behind the balancer; Redis keeps them in sync so they can all
serve the same rooms.

**What “load balancer” means here:** It’s any layer that fronts multiple
`fastapi_chat.py` instances and fans incoming requests/WebSocket upgrades out to
them—e.g., an AWS ALB/NLB, Kubernetes Service/Ingress, Nginx/HAProxy/Envoy, or a
PaaS router. The balancer handles health checks and typically round-robins
requests, while Redis keeps every replica’s room stream consistent so users see
the same chat regardless of which instance they hit.

**How it’s implemented here:** The repository doesn’t ship a load balancer;
you supply one in your environment. Run multiple `fastapi_chat.py` instances
and front them with your chosen balancer. For example, with Nginx you could
define an upstream to your app replicas and proxy both HTTP and WebSocket
traffic to them:

```
upstream chat_api {
    server app1:8000;
    server app2:8000;
}

server {
    listen 80;
    location /ws/ {
        proxy_pass http://chat_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
    location / {
        proxy_pass http://chat_api;
    }
}
```

Any equivalent layer-7 load balancer (cloud-managed, ingress controller, or
reverse proxy) works the same way: it owns the public endpoint, distributes
incoming requests to your replicas, and Redis keeps each instance in sync.

**Is a load balancer built in?** No. The FastAPI service only exposes HTTP and
WebSocket endpoints; it does not embed a proxy. When you run a single instance
locally (e.g., `uvicorn fastapi_chat:app --port 8000`), there is no need for a
balancer. To scale out, start multiple app instances and place them behind an
external layer-7 balancer (cloud LB, ingress controller, Nginx/HAProxy/Envoy,
etc.) that owns the public port and forwards traffic to each replica.

#### Kubernetes / AWS EKS example (multi-region with HTTPS ingress)

- **Primary cluster in Region A (e.g., `us-east-1`)** runs your `fastapi_chat.py`
  replicas as a Deployment, fronted by a Service (type `ClusterIP`) and an
  ingress controller (AWS ALB Ingress Controller / AWS Load Balancer Controller
  or Nginx Ingress) that terminates HTTPS and load balances to the pods.
- **Secondary cluster in Region B (e.g., `us-west-2`)** mirrors the setup for
  disaster recovery. Keep the same Redis/PostgreSQL connection strings or point
  to region-specific managed services, and use DNS failover (e.g., Route 53)
  to shift traffic if Region A is unavailable.
- **Ingress controller:** either ALB/ELB via the AWS Load Balancer Controller or
  an in-cluster Nginx ingress exposes `https://` endpoints and handles WebSocket
  upgrades for `/ws/...` while proxying `POST /api/send` and `GET /api/history`.
  Configure health checks to hit `/health` so unhealthy pods are removed from
  rotation.

Clients can page through durable history via:

- `GET /api/history?room=<room>&limit=50&before_id=<id>`

#### Docker run

```bash
docker build -t mini-zoom-fastapi .
docker run -p 8000:8000 \ \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \ \
  -e DATABASE_URL=postgresql://chatuser:chatpass@host.docker.internal:5432/chatdb \ \
  mini-zoom-fastapi
```

#### Quick WebSocket test

```bash
websocat ws://localhost:8000/ws/lobby/alice
# In another shell:
websocat ws://localhost:8000/ws/lobby/bob
```

Messages flow through Redis, so both shells (and any additional app replicas)
share the same rooms without sticky sessions or local memory.

#### How fan-out works (Redis pub/sub)

Redis pub/sub is used so every app instance hears the same room events without
keeping per-room state in-process:

1. **Sender → API:** a client sends a chat message via `POST /api/send` or over
   the WebSocket route `WS /ws/{room}/{username}`.
2. **API → Redis:** the API records the message in PostgreSQL for durability and
   publishes a JSON payload to `chat-room:<room>` using `PUBLISH`.
3. **Redis → all replicas:** every running FastAPI instance has a `SUBSCRIBE` to
   that `chat-room:<room>` channel. Redis fan-outs the payload to all of them,
   so no single process is a bottleneck.
4. **Replica → clients:** each replica forwards the payload to its connected
   WebSocket clients for that room. Clients on different app instances still
   see the same stream because Redis delivered the same message to every
   subscriber.

Examples:

- If **Alice** posts in `lobby` via `POST /api/send`, the process that handled
  the request publishes `{"username": "alice", "text": "hi", ...}` to
  `chat-room:lobby`; every replica receives it and forwards it to its own
  WebSocket connections in `lobby`.
- If **Bob** is connected to replica A and **Cara** to replica B, and Alice’s
  message hits replica C, Redis delivers the payload to A, B, and C so Bob and
  Cara both see Alice’s chat immediately without sticky sessions.

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
