from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

from ..brain import brain

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await brain.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "chat":
                text = msg.get("content", "").strip()
                if text:
                    await brain.on_user_message(text, ws)

            elif msg_type == "interact":
                action = msg.get("action", "click")
                await brain.on_interact(action)

            elif msg_type == "mode":
                mode = msg.get("mode", "")
                await brain.set_mode(mode)

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        brain.disconnect(ws)
    except Exception as e:
        print(f"[WS] error: {e}")
        brain.disconnect(ws)
