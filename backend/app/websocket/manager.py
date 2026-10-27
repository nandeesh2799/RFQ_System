import json
import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("websocket")


class ConnectionManager:
    """Manages WebSocket connections and room broadcasts for real-time auction updates."""

    def __init__(self):
        # rfq_id -> set of WebSockets
        self.auction_rooms: Dict[int, Set[WebSocket]] = {}
        # general subscribers (e.g., dashboard or auction listing)
        self.general_subscribers: Set[WebSocket] = set()

    async def connect_general(self, websocket: WebSocket):
        await websocket.accept()
        self.general_subscribers.add(websocket)

    def disconnect_general(self, websocket: WebSocket):
        self.general_subscribers.discard(websocket)

    async def connect_auction(self, rfq_id: int, websocket: WebSocket):
        await websocket.accept()
        if rfq_id not in self.auction_rooms:
            self.auction_rooms[rfq_id] = set()
        self.auction_rooms[rfq_id].add(websocket)

    def disconnect_auction(self, rfq_id: int, websocket: WebSocket):
        if rfq_id in self.auction_rooms:
            self.auction_rooms[rfq_id].discard(websocket)
            if not self.auction_rooms[rfq_id]:
                del self.auction_rooms[rfq_id]

    async def broadcast_to_auction(self, rfq_id: int, message: Dict[str, Any]):
        """Broadcasts an event message to all clients watching a specific RFQ auction."""
        text = json.dumps(message, default=str)
        sockets = self.auction_rooms.get(rfq_id, set()).copy()
        dead = []
        for ws in sockets:
            try:
                await ws.send_text(text)
            except Exception as e:
                logger.warning(f"Failed to send to client in room {rfq_id}: {e}")
                dead.append(ws)
        for ws in dead:
            self.disconnect_auction(rfq_id, ws)

    async def broadcast_to_general(self, message: Dict[str, Any]):
        """Broadcasts a global event to all listing/dashboard clients."""
        text = json.dumps(message, default=str)
        dead = []
        for ws in self.general_subscribers.copy():
            try:
                await ws.send_text(text)
            except Exception as e:
                logger.warning(f"Failed to send to general subscriber: {e}")
                dead.append(ws)
        for ws in dead:
            self.disconnect_general(ws)


ws_manager = ConnectionManager()
