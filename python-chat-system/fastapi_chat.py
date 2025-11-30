import asyncio
import contextlib
import json
import os
import time
from typing import Any, Dict, Optional

import asyncpg
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import redis.asyncio as redis


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://chatuser:chatpass@localhost:5432/chatdb")
CHANNEL_PREFIX = "chat-room:"  # ensures isolation from other redis data

MVP_HTML = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Mini Zoom Chat</title>
  <style>
    body { font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0b1222; color: #e6ecf5; margin: 0; }
    .shell { max-width: 760px; margin: 0 auto; padding: 20px; }
    header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
    .pill { background: #1f2a44; padding: 6px 12px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; color: #9fb2e1; }
    h1 { margin: 0; font-size: 22px; }
    .card { background: #0f1629; border: 1px solid #1f2b45; border-radius: 14px; padding: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.35); margin-bottom: 14px; }
    label { display: block; font-size: 13px; color: #94a7d6; margin-bottom: 6px; }
    input { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid #1f2b45; background: #0c1323; color: #e6ecf5; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    button { background: linear-gradient(135deg, #3a8bfd, #6f7cff); border: none; padding: 10px 14px; border-radius: 10px; color: #fff; font-weight: 600; cursor: pointer; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    #log { height: 320px; overflow-y: auto; background: #050915; border: 1px solid #1f2b45; border-radius: 12px; padding: 12px; font-family: "SFMono-Regular", Consolas, monospace; font-size: 13px; }
    .msg { margin-bottom: 8px; line-height: 1.35; }
    .meta { color: #8ea1c7; margin-right: 8px; }
    .info { color: #9dd58c; }
    .error { color: #ffb4a2; }
    form.send { display: flex; gap: 10px; margin-top: 12px; }
    form.send input { flex: 1; }
  </style>
</head>
<body>
  <div class=\"shell\">
    <header>
      <div class=\"pill\">Minimal MVP</div>
      <h1>Mini Zoom Chat</h1>
    </header>

    <div class=\"card\">
      <div class=\"row\">
        <div>
          <label for=\"username\">Username</label>
          <input id=\"username\" placeholder=\"alice\" />
        </div>
        <div>
          <label for=\"room\">Room</label>
          <input id=\"room\" placeholder=\"lobby\" />
        </div>
      </div>
      <div style=\"margin-top:12px; display:flex; gap:10px; align-items:center;\">
        <button id=\"connectBtn\">Join room</button>
        <span id=\"status\">Disconnected</span>
      </div>
    </div>

    <div class=\"card\">
      <div id=\"log\" aria-live=\"polite\"></div>
      <form class=\"send\" id=\"sendForm\">
        <input id=\"messageInput\" placeholder=\"Say something...\" autocomplete=\"off\" />
        <button type=\"submit\">Send</button>
      </form>
    </div>
  </div>

  <script>
    const state = { socket: null, room: '', username: '' };
    const logEl = document.getElementById('log');
    const statusEl = document.getElementById('status');
    const sendForm = document.getElementById('sendForm');
    const messageInput = document.getElementById('messageInput');

    function renderMessage(msg) {
      const el = document.createElement('div');
      el.className = 'msg';
      const meta = document.createElement('span');
      meta.className = 'meta';
      if (msg.type === 'info') meta.classList.add('info');
      meta.textContent = `[${msg.room}] ${msg.username}`;
      const body = document.createElement('span');
      body.textContent = ` ${msg.text}`;
      if (msg.type === 'error') body.className = 'error';
      el.append(meta, body);
      logEl.appendChild(el);
      logEl.scrollTop = logEl.scrollHeight;
    }

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function connect() {
      const username = document.getElementById('username').value.trim();
      const room = document.getElementById('room').value.trim();
      if (!username || !room) {
        alert('Enter username and room');
        return;
      }
      state.room = room;
      state.username = username;
      const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${encodeURIComponent(room)}/${encodeURIComponent(username)}`;
      state.socket = new WebSocket(url);
      setStatus('Connecting...');
      state.socket.onopen = () => setStatus(`Joined ${room} as ${username}`);
      state.socket.onclose = () => setStatus('Disconnected');
      state.socket.onerror = () => setStatus('Error');
      state.socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          renderMessage(payload);
        } catch (err) {
          renderMessage({ room, username: 'system', text: 'Failed to parse message', type: 'error' });
        }
      };
    }

    document.getElementById('connectBtn').addEventListener('click', connect);

    sendForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
        alert('Join a room first');
        return;
      }
      const text = messageInput.value.trim();
      if (!text) return;
      messageInput.value = '';
      state.socket.send(text);
    });
  </script>
</body>
</html>
"""

app = FastAPI(title="Mini Zoom Chat API", version="0.1.0")


async def get_redis() -> redis.Redis:
    if not hasattr(app.state, "redis_client"):
        app.state.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return app.state.redis_client


async def get_pg_pool() -> asyncpg.Pool:
    if not hasattr(app.state, "pg_pool"):
        app.state.pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return app.state.pg_pool


async def init_postgres() -> None:
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGSERIAL PRIMARY KEY,
                room TEXT NOT NULL,
                username TEXT NOT NULL,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_chat_messages_room_id ON chat_messages (room, id DESC);
            """
        )


async def record_message(room: str, username: str, text: str, msg_type: str, ts: Optional[float] = None) -> Dict[str, Any]:
    pool = await get_pg_pool()
    ts = ts if ts is not None else time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO chat_messages (room, username, text, type, ts)
            VALUES ($1, $2, $3, $4, to_timestamp($5))
            RETURNING id, extract(epoch from ts) as ts
            """,
            room,
            username,
            text,
            msg_type,
            ts,
        )
    return {"id": row["id"], "ts": row["ts"]}


async def fetch_history(room: str, before_id: Optional[int], limit: int) -> Dict[str, Any]:
    pool = await get_pg_pool()
    clauses = ["room = $1"]
    params: list[Any] = [room]
    if before_id is not None:
        clauses.append("id < $2")
        params.append(before_id)
    query = "SELECT id, room, username, text, type, extract(epoch from ts) as ts FROM chat_messages WHERE " + " AND ".join(clauses) + " ORDER BY id DESC LIMIT $" + str(len(params) + 1)
    params.append(limit)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    # return ascending order for client readability
    messages = [dict(row) for row in reversed(rows)]
    return {"messages": messages}


async def publish_message(room: str, payload: Dict[str, Any]) -> None:
    payload.setdefault("room", room)
    payload.setdefault("ts", time.time())
    meta = await record_message(room, payload.get("username", ""), payload.get("text", ""), payload.get("type", "chat"), payload["ts"])
    payload.setdefault("id", meta["id"])

    client = await get_redis()
    await client.publish(f"{CHANNEL_PREFIX}{room}", json.dumps(payload))


@app.on_event("startup")
async def startup():
    await init_postgres()


@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "redis_client"):
        await app.state.redis_client.aclose()
    if hasattr(app.state, "pg_pool"):
        await app.state.pg_pool.close()


@app.get("/", response_class=HTMLResponse)
async def home():
    return MVP_HTML


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/api/history")
async def history(room: str, limit: int = 50, before_id: Optional[int] = None):
    room = (room or "").strip()
    if not room:
        raise HTTPException(status_code=400, detail="room is required")
    limit = max(1, min(limit, 500))
    return await fetch_history(room, before_id, limit)


@app.post("/api/send")
async def send_message(data: Dict[str, Any]):
    room = (data.get("room") or "").strip()
    username = (data.get("username") or "").strip()
    text = (data.get("text") or "").strip()

    if not room or not username or not text:
        raise HTTPException(status_code=400, detail="room, username, and text are required")

    message = {"username": username, "text": text, "type": "chat"}
    await publish_message(room, message)
    return JSONResponse({"ok": True})


@app.websocket("/ws/{room}/{username}")
async def websocket_chat(websocket: WebSocket, room: str, username: str):
    room = room.strip()
    username = username.strip()
    if not room or not username:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    client = await get_redis()
    channel = f"{CHANNEL_PREFIX}{room}"
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)

    async def reader():
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                payload = json.loads(message["data"])
                try:
                    await websocket.send_json(payload)
                except Exception:
                    break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    reader_task = asyncio.create_task(reader())

    await publish_message(room, {"username": username, "text": f"{username} joined {room}", "type": "info"})

    try:
        while True:
            msg_text = await websocket.receive_text()
            text = msg_text.strip()
            if text:
                await publish_message(room, {"username": username, "text": text, "type": "chat"})
    except WebSocketDisconnect:
        await publish_message(room, {"username": username, "text": f"{username} left {room}", "type": "info"})
    finally:
        reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reader_task


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
