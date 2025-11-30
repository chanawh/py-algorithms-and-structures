import asyncio
import contextlib
import json
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import redis.asyncio as redis


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CHANNEL_PREFIX = "chat-room:"  # ensures isolation from other redis data

app = FastAPI(title="Mini Zoom Chat API", version="0.1.0")


async def get_redis() -> redis.Redis:
    if not hasattr(app.state, "redis_client"):
        app.state.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return app.state.redis_client


async def publish_message(room: str, payload: Dict[str, Any]) -> None:
    payload.setdefault("room", room)
    payload.setdefault("ts", time.time())
    client = await get_redis()
    await client.publish(f"{CHANNEL_PREFIX}{room}", json.dumps(payload))


@app.on_event("shutdown")
async def close_redis():
    if hasattr(app.state, "redis_client"):
        await app.state.redis_client.aclose()


@app.get("/health")
async def health():
    return {"ok": True}


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
