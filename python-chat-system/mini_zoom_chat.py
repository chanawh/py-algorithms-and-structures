"""
Mini Zoom Chat – a tiny long-polling web chat UI served with the Python standard library.

Run:
    python mini_zoom_chat.py --host 0.0.0.0 --port 8000
Open http://localhost:8000 in your browser, choose a username/room, and chat.
"""

import argparse
import itertools
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CHAT_HTML = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Mini Zoom Chat</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f7f7f7; }
    .shell { max-width: 720px; margin: 0 auto; padding: 16px; }
    header { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #2b303b; color: #fff; border-radius: 10px; }
    header h1 { margin: 0; font-size: 20px; }
    .pill { background: #394150; border-radius: 20px; padding: 6px 12px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
    .card { background: #fff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); padding: 16px; margin-top: 18px; }
    label { font-size: 13px; color: #555; display: block; margin-bottom: 6px; }
    input { width: 100%; padding: 10px 12px; border: 1px solid #d5d5d5; border-radius: 8px; font-size: 14px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    button { background: #1f8feb; border: none; color: #fff; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    #log { background: #0c111b; color: #e8ecf5; height: 320px; overflow-y: auto; border-radius: 10px; padding: 12px; font-family: "SFMono-Regular", Consolas, monospace; font-size: 13px; }
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
      <div class=\"pill\">Mini Zoom Chat</div>
      <h1>Simple web UI</h1>
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
const state = { room: '', username: '', lastId: 0, connected: false };
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

async function joinRoom() {
  const username = document.getElementById('username').value.trim();
  const room = document.getElementById('room').value.trim();
  if (!username || !room) {
    alert('Enter username and room');
    return;
  }
  state.room = room;
  state.username = username;
  state.lastId = 0;
  setStatus('Connecting...');
  try {
    await fetch('/api/join', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room, username }) });
    state.connected = true;
    setStatus(`Joined ${room} as ${username}`);
    renderMessage({ room, username: 'system', text: `Joined ${room}`, type: 'info' });
    pollLoop();
  } catch (err) {
    setStatus('Join failed');
    renderMessage({ room, username: 'system', text: err.message, type: 'error' });
  }
}

document.getElementById('connectBtn').addEventListener('click', joinRoom);

sendForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!state.connected) {
    alert('Join a room first');
    return;
  }
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = '';
  try {
    await fetch('/api/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room: state.room, username: state.username, text }) });
  } catch (err) {
    renderMessage({ room: state.room, username: 'system', text: err.message, type: 'error' });
  }
});

async function pollLoop() {
  while (state.connected) {
    try {
      const res = await fetch(`/api/poll?room=${encodeURIComponent(state.room)}&after=${state.lastId}`);
      const data = await res.json();
      if (Array.isArray(data.messages)) {
        data.messages.forEach(renderMessage);
        if (data.messages.length) {
          state.lastId = data.messages[data.messages.length - 1].id;
        }
      }
    } catch (err) {
      renderMessage({ room: state.room, username: 'system', text: 'Connection lost, retrying...', type: 'error' });
      await new Promise(r => setTimeout(r, 1500));
    }
  }
}
</script>
</body>
</html>
"""

rooms = {}
rooms_lock = threading.Lock()
message_ids = itertools.count(1)
# Keep room history bounded to prevent unbounded memory growth if a room stays active.
MAX_MESSAGES_PER_ROOM = 500


def get_room(room: str):
    with rooms_lock:
        if room not in rooms:
            rooms[room] = {"messages": [], "cond": threading.Condition()}
        return rooms[room]


def append_message(room: str, username: str, text: str, msg_type: str = "chat"):
    room_data = get_room(room)
    message_id = next(message_ids)
    message = {
        "id": message_id,
        "room": room,
        "username": username,
        "text": text,
        "type": msg_type,
    }
    with room_data["cond"]:
        room_data["messages"].append(message)
        if len(room_data["messages"]) > MAX_MESSAGES_PER_ROOM:
            room_data["messages"] = room_data["messages"][-MAX_MESSAGES_PER_ROOM:]
        room_data["cond"].notify_all()
    return message


def wait_for_messages(room: str, after: int, timeout: float = 20.0):
    room_data = get_room(room)
    deadline = time.time() + timeout
    with room_data["cond"]:
        while True:
            pending = [m for m in room_data["messages"] if m["id"] > after]
            if pending:
                return pending
            remaining = deadline - time.time()
            if remaining <= 0:
                return []
            room_data["cond"].wait(timeout=remaining)


class ChatHandler(BaseHTTPRequestHandler):
    server_version = "MiniZoomChat/0.1"

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def send_json(self, status_code: int, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = CHAT_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/poll":
            qs = parse_qs(parsed.query)
            room = qs.get("room", [None])[0]
            after_raw = qs.get("after", ["0"])[0]
            if not room:
                self.send_json(400, {"error": "room required"})
                return
            try:
                after = int(after_raw)
            except ValueError:
                self.send_json(400, {"error": "after must be an integer"})
                return
            messages = wait_for_messages(room, after)
            self.send_json(200, {"messages": messages})
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        data = self._read_json() or {}

        if parsed.path == "/api/join":
            room = (data.get("room") or "").strip()
            username = (data.get("username") or "").strip()
            if not room or not username:
                self.send_json(400, {"error": "room and username are required"})
                return
            append_message(room, username, f"{username} joined {room}", "info")
            self.send_json(200, {"ok": True})
            return

        if parsed.path == "/api/send":
            room = (data.get("room") or "").strip()
            username = (data.get("username") or "").strip()
            text = (data.get("text") or "").strip()
            if not room or not username or not text:
                self.send_json(400, {"error": "room, username, and text are required"})
                return
            append_message(room, username, text, "chat")
            self.send_json(200, {"ok": True})
            return

        self.send_json(404, {"error": "not found"})


def parse_args():
    parser = argparse.ArgumentParser(description="Mini Zoom Chat web UI server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    return parser.parse_args()


def run_server(host: str, port: int):
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"[INFO] Mini Zoom Chat running on http://{host}:{port}")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down server")
    finally:
        server.server_close()


if __name__ == "__main__":
    args = parse_args()
    run_server(args.host, args.port)
