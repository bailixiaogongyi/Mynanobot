import asyncio
import re
from typing import Any
from loguru import logger
from collections import defaultdict


class PubSubManager:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._patterns: dict[str, re.Pattern] = {}

    def subscribe(self, topic: str, queue: asyncio.Queue) -> None:
        self._subscribers[topic].append(queue)
        logger.debug(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, queue: asyncio.Queue) -> None:
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(queue)
            except ValueError:
                pass

    async def publish(self, topic: str, message: Any) -> None:
        for queue in self._subscribers.get(topic, []):
            await queue.put(message)

        for pattern, regex in self._patterns.items():
            if regex.search(topic):
                for queue in self._subscribers.get(pattern, []):
                    await queue.put(message)

    def subscribe_pattern(self, pattern: str, queue: asyncio.Queue) -> None:
        regex_pattern = pattern.replace("*", ".*")
        self._patterns[pattern] = re.compile(f"^{regex_pattern}$")
        self._subscribers[pattern].append(queue)

    def get_subscribers(self, topic: str) -> int:
        count = len(self._subscribers.get(topic, []))
        for pattern, regex in self._patterns.items():
            if regex.search(topic):
                count += len(self._subscribers.get(pattern, []))
        return count


class AgentChannel:
    def __init__(self, pubsub: PubSubManager, agent_id: str):
        self.pubsub = pubsub
        self.agent_id = agent_id
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._my_topics: set[str] = set()
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        self.pubsub.subscribe(f"agent.{self.agent_id}", self._inbox)
        self._my_topics.add(f"agent.{self.agent_id}")

    def send_to_agent(self, agent_id: str, message: Any) -> None:
        asyncio.create_task(self.pubsub.publish(f"agent.{agent_id}", {
            "from": self.agent_id,
            "message": message
        }))

    async def receive(self, timeout: float = 30.0) -> Any | None:
        try:
            return await asyncio.wait_for(self._inbox.get(), timeout)
        except asyncio.TimeoutError:
            return None

    def broadcast(self, message: Any) -> None:
        asyncio.create_task(self.pubsub.publish("agent.broadcast", {
            "from": self.agent_id,
            "message": message
        }))

    def cleanup(self) -> None:
        for topic in self._my_topics:
            self.pubsub.unsubscribe(topic, self._inbox)
        self._my_topics.clear()
