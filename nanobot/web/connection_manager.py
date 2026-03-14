"""WebSocket connection manager for Web UI notifications."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from loguru import logger

from nanobot.bus.events import OutboundMessage


class WebConnectionManager:
    """
    Manages WebSocket connections for the Web UI.
    
    This manager tracks active WebSocket connections and allows
    pushing notifications to specific chat sessions.
    
    Used for:
    - Pushing scheduled task notifications
    - Pushing heartbeat notifications
    - Real-time updates without user interaction
    """
    
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, chat_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket connection for a chat session."""
        async with self._lock:
            if chat_id in self._connections:
                old_ws = self._connections[chat_id]
                try:
                    await old_ws.close(code=1000, reason="Replaced by new connection")
                except Exception:
                    pass
            self._connections[chat_id] = websocket
            logger.info(f"[WebConnectionManager] Registered connection for chat_id={chat_id}, total={len(self._connections)}")
    
    async def unregister(self, chat_id: str) -> None:
        """Unregister a WebSocket connection."""
        async with self._lock:
            if chat_id in self._connections:
                del self._connections[chat_id]
                logger.info(f"[WebConnectionManager] Unregistered connection for chat_id={chat_id}, total={len(self._connections)}")
    
    def is_connected(self, chat_id: str) -> bool:
        """Check if a chat session has an active connection."""
        return chat_id in self._connections
    
    def get_connected_chats(self) -> list[str]:
        """Get list of currently connected chat IDs."""
        return list(self._connections.keys())
    
    async def send_to_chat(self, chat_id: str, message: dict[str, Any]) -> bool:
        """
        Send a message to a specific chat session.
        
        Args:
            chat_id: Target chat ID.
            message: Message dict to send.
        
        Returns:
            True if sent successfully, False otherwise.
        """
        async with self._lock:
            websocket = self._connections.get(chat_id)
            if not websocket:
                logger.debug(f"[WebConnectionManager] No connection for chat_id={chat_id}")
                return False
            
            try:
                await websocket.send_json(message)
                logger.debug(f"[WebConnectionManager] Sent message to chat_id={chat_id}")
                return True
            except Exception as e:
                logger.warning(f"[WebConnectionManager] Failed to send to chat_id={chat_id}: {e}")
                del self._connections[chat_id]
                return False
    
    async def broadcast(self, message: dict[str, Any]) -> int:
        """
        Broadcast a message to all connected sessions.
        
        Args:
            message: Message dict to send.
        
        Returns:
            Number of sessions the message was sent to.
        """
        sent = 0
        async with self._lock:
            disconnected = []
            for chat_id, websocket in self._connections.items():
                try:
                    await websocket.send_json(message)
                    sent += 1
                except Exception as e:
                    logger.warning(f"[WebConnectionManager] Failed to broadcast to chat_id={chat_id}: {e}")
                    disconnected.append(chat_id)
            
            for chat_id in disconnected:
                del self._connections[chat_id]
        
        logger.info(f"[WebConnectionManager] Broadcast to {sent} sessions")
        return sent
    
    async def handle_outbound(self, msg: OutboundMessage) -> bool:
        """
        Handle an outbound message for the web channel.
        
        Args:
            msg: OutboundMessage with channel='web'.
        
        Returns:
            True if sent successfully, False otherwise.
        """
        if msg.channel != "web":
            return False
        
        message = {
            "type": "notification",
            "content": msg.content,
            "chat_id": msg.chat_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        if msg.metadata:
            message["metadata"] = msg.metadata
        
        return await self.send_to_chat(msg.chat_id, message)


_manager: WebConnectionManager | None = None


def get_web_connection_manager() -> WebConnectionManager:
    """Get the global WebConnectionManager instance."""
    global _manager
    if _manager is None:
        _manager = WebConnectionManager()
    return _manager
