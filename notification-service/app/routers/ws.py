from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
