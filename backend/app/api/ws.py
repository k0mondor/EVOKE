from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/realtime")
async def realtime_socket(websocket: WebSocket) -> None:
    hub = websocket.app.state.realtime_hub
    await hub.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            await hub.handle_command(websocket, message)
    except WebSocketDisconnect:
        hub.disconnect(websocket)
    except Exception:
        hub.disconnect(websocket)
