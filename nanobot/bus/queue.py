"""Async message queue for decoupled channel-agent communication."""

import asyncio
from pathlib import Path

from nanobot.bus.events import InboundMessage, OutboundMessage

MAX_QUEUE_SIZE = 1000


class MessageBus:
    """
    Enhanced message bus with pub/sub and shared context.

    Features:
    - Original queue-based messaging (backward compatible)
    - Pub/Sub for agent-to-agent communication
    - Shared context for collaboration
    """

    def __init__(self, max_size: int = MAX_QUEUE_SIZE):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue(maxsize=max_size)
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue(maxsize=max_size)

        from nanobot.bus.pubsub import PubSubManager
        self.pubsub = PubSubManager()

        self._shared_context = None

    def init_shared_context(self, workspace: Path) -> None:
        """Initialize shared context for agent collaboration."""
        from nanobot.bus.shared_context import SharedContext
        self._shared_context = SharedContext(workspace)

    @property
    def shared_context(self):
        """Get shared context instance."""
        return self._shared_context

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Publish a message from a channel to the agent."""
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """Consume the next inbound message (blocks until available)."""
        return await self.inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Publish a response from the agent to channels."""
        await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """Consume the next outbound message (blocks until available)."""
        return await self.outbound.get()

    @property
    def inbound_size(self) -> int:
        """Number of pending inbound messages."""
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """Number of pending outbound messages."""
        return self.outbound.qsize()
