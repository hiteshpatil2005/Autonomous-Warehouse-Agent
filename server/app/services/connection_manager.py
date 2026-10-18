"""
WareBot AI — WebSocket Connection Manager
Maintains active real-time client connections and handles broadcast distribution.
"""

import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("warebot.websocket")


class ConnectionManager:
    """Manages WebSocket connections and real-time event broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept incoming connection and register client."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Unregister client on disconnect."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast JSON payload to all active clients.
        Automatically removes dead/closed connections without failing.
        """
        if not self.active_connections:
            return

        dead_connections: List[WebSocket] = []

        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.debug(f"Failed to send to client ({exc}). Marking for removal.")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Global singleton connection manager
ws_manager = ConnectionManager()
