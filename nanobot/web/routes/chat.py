"""Chat API routes for Web UI.

This module provides chat-related API endpoints for the Web UI.
All sessions are prefixed with 'web:' to ensure isolation from other channels.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Query
from loguru import logger
from pydantic import BaseModel

from nanobot.providers.base import StreamChunk
from nanobot.web.connection_manager import get_web_connection_manager

if TYPE_CHECKING:
    from nanobot.agent.loop import AgentLoop
    from nanobot.session.manager import SessionManager

router = APIRouter()

CHANNEL_PREFIX = "web"


class ChatMessage(BaseModel):
    """Chat message request."""

    content: str
    chat_id: str = "default"
    attachments: list[dict[str, Any]] = []


class ChatResponse(BaseModel):
    """Chat message response."""

    content: str
    role: str = "assistant"
    chat_id: str


class SessionInfo(BaseModel):
    """Session information."""

    id: str
    name: str
    created_at: str
    updated_at: str
    message_count: int


class SessionCreate(BaseModel):
    """Session creation request."""

    name: str


def _get_session_key(chat_id: str) -> str:
    """Build session key with web prefix.

    Args:
        chat_id: User-provided chat ID.

    Returns:
        Full session key in format 'web:{chat_id}'.
    """
    return f"{CHANNEL_PREFIX}:{chat_id}"


def _get_agent(request) -> AgentLoop:
    """Get agent from app state."""
    return request.app.state.agent


def _get_session_manager(request) -> SessionManager:
    """Get session manager from app state."""
    return request.app.state.session_manager


def _get_workspace(request) -> "Path":
    """Get workspace path from app state."""
    return request.app.state.config.workspace_path


@router.post("/send", response_model=ChatResponse)
async def send_message(message: ChatMessage, request: Request) -> ChatResponse:
    """Send a message and get response.

    Session key is automatically built as 'web:{chat_id}'.

    Args:
        message: Chat message with content and optional chat_id.

    Returns:
        Assistant's response.
    """
    agent = _get_agent(request)
    session_key = _get_session_key(message.chat_id)

    media = None
    if message.attachments:
        media = [att.get("path", "") for att in message.attachments if att.get("path")]

    try:
        response = await agent.process_direct(
            message.content,
            session_key=session_key,
            channel=CHANNEL_PREFIX,
            chat_id=message.chat_id,
            media=media,
        )
        return ChatResponse(
            content=response or "",
            role="assistant",
            chat_id=message.chat_id,
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


WEBSOCKET_PING_INTERVAL_DEFAULT = 30
WEBSOCKET_PING_INTERVAL_IDLE = 120
WEBSOCKET_PING_TIMEOUT = 300

_active_stream_tasks: dict[str, asyncio.Task] = {}


@router.websocket("/ws/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for real-time streaming chat.

    Session key is automatically built as 'web:{chat_id}'.

    Includes heartbeat mechanism to keep connections alive and detect stale connections.

    Supports streaming LLM responses with the following message types:
    - text_delta: Incremental text content
    - reasoning_delta: Reasoning/thinking content (for models like DeepSeek-R1)
    - tool_start: Tool call started
    - tool_result: Tool execution result
    - status: Status update (e.g., "thinking")
    - done: Final response complete
    - error: Error occurred
    - ping/pong: Heartbeat
    - notification: Push notification from scheduled tasks

    Args:
        websocket: WebSocket connection.
        chat_id: Chat/session ID.
    """
    logger.info(f"[WS] New WebSocket connection request for chat_id={chat_id}")
    await websocket.accept()
    logger.info(f"[WS] WebSocket accepted for chat_id={chat_id}")
    
    agent = websocket.app.state.agent
    session_key = _get_session_key(chat_id)
    connection_manager = get_web_connection_manager()

    await connection_manager.register(chat_id, websocket)

    last_pong_time = datetime.now()
    heartbeat_task = None

    async def send_chunk(chunk: StreamChunk):
        """Send a stream chunk to the client."""
        try:
            if websocket.client_state.name != "CONNECTED":
                logger.debug(f"[WS] WebSocket not connected, skipping chunk")
                return
            msg: dict[str, Any] = {
                "type": chunk.type,
                "content": chunk.content or "",
                "chat_id": chat_id,
                "timestamp": datetime.now().isoformat(),
            }
            if chunk.metadata:
                msg["metadata"] = chunk.metadata
            elif chunk.tool_call:
                msg["metadata"] = {
                    "tool_name": chunk.tool_call.name,
                    "tool_args": chunk.tool_call.arguments,
                }
            if chunk.finish_reason:
                msg["finish_reason"] = chunk.finish_reason
            if chunk.usage:
                msg["usage"] = chunk.usage
            await websocket.send_json(msg)
            logger.debug(f"[WS] Sent chunk: type={chunk.type}")
        except Exception as e:
            logger.debug(f"[WS] Error sending chunk: {e}")

    async def heartbeat_sender():
        """Send periodic ping messages and check for pong responses with dynamic interval."""
        nonlocal last_pong_time
        last_message_time = datetime.now()
        
        while True:
            now = datetime.now()
            time_since_last_msg = (now - last_message_time).total_seconds()
            interval = WEBSOCKET_PING_INTERVAL_IDLE if time_since_last_msg > 60 else WEBSOCKET_PING_INTERVAL_DEFAULT
            
            try:
                await asyncio.sleep(interval)
                await websocket.send_json({"type": "ping"})
                if (datetime.now() - last_pong_time).total_seconds() > WEBSOCKET_PING_TIMEOUT:
                    logger.warning(f"WebSocket heartbeat timeout for {chat_id}, closing")
                    await websocket.close(code=1001, reason="Heartbeat timeout")
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat sender error for {chat_id}: {e}")
                break
    
    heartbeat_task = asyncio.create_task(heartbeat_sender())

    try:
        last_message_time = datetime.now()
        
        while True:
            data = await websocket.receive_text()
            last_message_time = datetime.now()
            logger.info(f"[WS] Received data: {data[:100]}...")

            try:
                import json
                msg = json.loads(data)
                if msg.get("type") == "pong":
                    last_pong_time = datetime.now()
                    continue
                if msg.get("type") == "cancel":
                    cancel_chat_id = msg.get("chat_id", chat_id)
                    logger.info(f"Received cancel request for {cancel_chat_id}")
                    if cancel_chat_id in _active_stream_tasks:
                        task = _active_stream_tasks[cancel_chat_id]
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        del _active_stream_tasks[cancel_chat_id]
                        logger.info(f"Cancelled stream task for {cancel_chat_id}")
                    await websocket.send_json({
                        "type": "cancelled",
                        "chat_id": cancel_chat_id,
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                if isinstance(msg, dict) and "content" in msg:
                    content = msg.get("content", "")
                    raw_attachments = msg.get("attachments", [])
                    if raw_attachments and isinstance(raw_attachments, list):
                        media = [att.get("path", "") for att in raw_attachments if att.get("path")]
                    else:
                        media = []
                    data = content
                else:
                    media = []
                    data = ""
            except json.JSONDecodeError as e:
                logger.warning(f"[WS] Invalid JSON received from {chat_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format. Please send valid JSON.",
                    "chat_id": chat_id,
                    "timestamp": datetime.now().isoformat(),
                })
                continue

            try:
                logger.info(f"[WS] Calling process_stream for chat_id={chat_id}")
                
                async def run_stream():
                    await agent.process_stream(
                        data,
                        session_key=session_key,
                        channel=CHANNEL_PREFIX,
                        chat_id=chat_id,
                        on_chunk=send_chunk,
                        media=media if media else None,
                    )
                
                stream_task = asyncio.create_task(run_stream())
                _active_stream_tasks[chat_id] = stream_task
                
                try:
                    await stream_task
                except asyncio.CancelledError:
                    logger.info(f"[WS] Stream cancelled for chat_id={chat_id}")
                    await websocket.send_json({
                        "type": "cancelled",
                        "chat_id": chat_id,
                        "timestamp": datetime.now().isoformat(),
                    })
                finally:
                    _active_stream_tasks.pop(chat_id, None)
                
                logger.info(f"[WS] process_stream completed for chat_id={chat_id}")
            except Exception as e:
                logger.error(f"[WS] Error in process_stream: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": str(e),
                    "chat_id": chat_id,
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {chat_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await connection_manager.unregister(chat_id)
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> list[SessionInfo]:
    """List all sessions for the web channel with pagination.

    Args:
        request: FastAPI request object.
        page: Page number (starting from 1).
        page_size: Number of items per page (max 100).

    Returns:
        List of session information.
    """
    session_manager = _get_session_manager(request)

    sessions_dir = session_manager.sessions_dir
    if not sessions_dir.exists():
        return []

    session_files = sorted(
        sessions_dir.glob("web_*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_files = session_files[start_idx:end_idx]

    sessions = []
    for session_file in paginated_files:
        session_key = session_file.stem
        chat_id = session_key.replace("web_", "")

        stat = session_file.stat()
        sessions.append(SessionInfo(
            id=chat_id,
            name=chat_id.replace("-", " ").replace("_", " ").title(),
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            updated_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            message_count=_count_messages(session_file),
        ))

    return sessions


@router.post("/sessions", response_model=SessionInfo)
async def create_session(session: SessionCreate, request: Request) -> SessionInfo:
    """Create a new session.

    Session key is automatically built as 'web:{name}'.

    Args:
        session: Session creation request with name.

    Returns:
        Created session information.
    """
    session_manager = _get_session_manager(request)
    chat_id = session.name.lower().replace(" ", "-").replace("_", "-")
    session_key = _get_session_key(chat_id)

    session_obj = session_manager.get_or_create(session_key)
    session_manager.save(session_obj)

    return SessionInfo(
        id=chat_id,
        name=session.name,
        created_at=session_obj.created_at.isoformat(),
        updated_at=session_obj.updated_at.isoformat(),
        message_count=0,
    )


@router.delete("/sessions/{chat_id}")
async def delete_session(chat_id: str, request: Request):
    """Delete a session.

    Args:
        chat_id: Chat/session ID to delete.

    Returns:
        Success message.
    """
    session_manager = _get_session_manager(request)
    session_key = _get_session_key(chat_id)

    if not session_manager.delete(session_key):
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "chat_id": chat_id}


@router.get("/sessions/{chat_id}/history")
async def get_session_history(chat_id: str, request: Request, limit: int = 100):
    """Get session message history.

    Args:
        chat_id: Chat/session ID.
        limit: Maximum number of messages to return.

    Returns:
        List of messages in the session.
    """
    session_manager = _get_session_manager(request)
    session_key = _get_session_key(chat_id)

    session = session_manager.get(session_key)
    if not session:
        return {"messages": [], "chat_id": chat_id}

    messages = session.get_full_history(max_messages=limit)
    
    # Log for debugging
    tool_messages = [m for m in messages if m.get("tool_calls")]
    if tool_messages:
        logger.info(f"[History] Returning {len(messages)} messages, {len(tool_messages)} with tool_calls")
    
    return {
        "messages": messages,
        "chat_id": chat_id,
        "total": len(session.messages),
    }


@router.delete("/sessions/{chat_id}/history")
async def clear_session_history(chat_id: str, request: Request):
    """Clear all messages in a session.

    Args:
        chat_id: Chat/session ID.

    Returns:
        Success status.
    """
    session_manager = _get_session_manager(request)
    session_key = _get_session_key(chat_id)

    session = session_manager.get(session_key)
    if not session:
        return {"status": "cleared", "chat_id": chat_id, "message": "Session not found"}

    session.clear()
    session_manager.save(session)
    session_manager.invalidate(session_key)

    logger.info(f"[History] Cleared session {session_key}")
    return {"status": "cleared", "chat_id": chat_id}


def _count_messages(session_file: "Path") -> int:
    """Count messages in a session file.

    Args:
        session_file: Path to session JSONL file.

    Returns:
        Number of messages.
    """
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0
