"""Progress tracking system for multi-agent tasks."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from loguru import logger

from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus

if TYPE_CHECKING:
    from nanobot.agent.tasks.manager import TaskManager


class ProgressStage(Enum):
    """Stages of task execution."""
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressCheckpoint:
    """A checkpoint in task progress."""
    stage: ProgressStage
    progress: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    artifacts: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "progress": self.progress,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "artifacts": self.artifacts,
            "metrics": self.metrics,
        }


class ProgressTracker:
    """Tracks and reports progress for subagent tasks.
    
    Features:
    - Stage-based progress tracking
    - Pause/resume support
    - Progress reporting via message bus
    - Checkpoint history
    """
    
    PROGRESS_RANGES = {
        ProgressStage.INITIALIZING: (0, 10),
        ProgressStage.ANALYZING: (10, 20),
        ProgressStage.EXECUTING: (20, 90),
        ProgressStage.VERIFYING: (90, 95),
        ProgressStage.FINALIZING: (95, 100),
        ProgressStage.COMPLETED: (100, 100),
        ProgressStage.FAILED: (100, 100),
    }
    
    def __init__(self, task_id: str, bus: MessageBus | None = None, task_manager: "TaskManager | None" = None):
        """Initialize the progress tracker.
        
        Args:
            task_id: The task ID being tracked.
            bus: Optional message bus for progress notifications.
            task_manager: Optional task manager for updating task status.
        """
        self.task_id = task_id
        self.bus = bus
        self.task_manager = task_manager
        self.checkpoints: list[ProgressCheckpoint] = []
        self.current_stage = ProgressStage.INITIALIZING
        self.current_progress = 0
        self.current_message = ""
        
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        
        self._cancelled = False
    
    async def report(
        self,
        stage: ProgressStage,
        progress: int,
        message: str,
        artifacts: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Report progress update.
        
        This method will block if the task is paused.
        
        Args:
            stage: The current execution stage.
            progress: Progress percentage (0-100).
            message: Progress message.
            artifacts: Optional list of artifacts produced.
            metrics: Optional performance metrics.
        """
        await self._pause_event.wait()
        
        if self._cancelled:
            raise asyncio.CancelledError("Task was cancelled")
        
        checkpoint = ProgressCheckpoint(
            stage=stage,
            progress=progress,
            message=message,
            artifacts=artifacts or [],
            metrics=metrics or {},
        )
        
        self.checkpoints.append(checkpoint)
        self.current_stage = stage
        self.current_progress = progress
        self.current_message = message
        
        logger.debug(f"Task [{self.task_id}] progress: {progress}% - {message}")
        
        if self.task_manager:
            self.task_manager.update_task(
                self.task_id,
                progress=progress,
                progress_message=message,
            )
        
        if self.bus:
            await self._send_progress_update(checkpoint)
    
    async def report_stage_start(self, stage: ProgressStage, message: str = "") -> None:
        """Report the start of a stage.
        
        Args:
            stage: The stage starting.
            message: Optional message.
        """
        min_progress, _ = self.PROGRESS_RANGES.get(stage, (0, 0))
        stage_message = message or f"开始{self._get_stage_name(stage)}"
        await self.report(stage, min_progress, stage_message)
    
    async def report_stage_progress(self, stage: ProgressStage, progress_within_stage: float, message: str = "") -> None:
        """Report progress within a stage.
        
        Args:
            stage: The current stage.
            progress_within_stage: Progress within stage (0.0-1.0).
            message: Optional message.
        """
        min_progress, max_progress = self.PROGRESS_RANGES.get(stage, (0, 100))
        actual_progress = min_progress + (max_progress - min_progress) * progress_within_stage
        await self.report(stage, int(actual_progress), message)
    
    async def report_stage_complete(self, stage: ProgressStage, message: str = "") -> None:
        """Report completion of a stage.
        
        Args:
            stage: The completed stage.
            message: Optional message.
        """
        _, max_progress = self.PROGRESS_RANGES.get(stage, (0, 100))
        stage_message = message or f"{self._get_stage_name(stage)}完成"
        await self.report(stage, max_progress, stage_message)
    
    async def report_complete(self, message: str = "任务完成", artifacts: list[str] | None = None) -> None:
        """Report task completion.
        
        Args:
            message: Completion message.
            artifacts: Optional list of final artifacts.
        """
        await self.report(ProgressStage.COMPLETED, 100, message, artifacts)
    
    async def report_failure(self, error: str) -> None:
        """Report task failure.
        
        Args:
            error: Error message.
        """
        await self.report(ProgressStage.FAILED, self.current_progress, f"任务失败: {error}")
    
    def pause(self) -> None:
        """Pause the task."""
        self._paused = True
        self._pause_event.clear()
        logger.info(f"Task [{self.task_id}] paused at {self.current_progress}%")
    
    def resume(self) -> None:
        """Resume the task."""
        self._paused = False
        self._pause_event.set()
        logger.info(f"Task [{self.task_id}] resumed")
    
    def cancel(self) -> None:
        """Cancel the task."""
        self._cancelled = True
        self._paused = False
        self._pause_event.set()
        logger.info(f"Task [{self.task_id}] cancelled")
    
    def is_paused(self) -> bool:
        """Check if the task is paused."""
        return self._paused
    
    def is_cancelled(self) -> bool:
        """Check if the task is cancelled."""
        return self._cancelled
    
    def get_progress(self) -> dict[str, Any]:
        """Get current progress information.
        
        Returns:
            Dictionary with progress details.
        """
        return {
            "task_id": self.task_id,
            "stage": self.current_stage.value,
            "progress": self.current_progress,
            "message": self.current_message,
            "is_paused": self._paused,
            "is_cancelled": self._cancelled,
            "checkpoint_count": len(self.checkpoints),
        }
    
    def get_checkpoints(self) -> list[dict[str, Any]]:
        """Get all checkpoints.
        
        Returns:
            List of checkpoint dictionaries.
        """
        return [cp.to_dict() for cp in self.checkpoints]
    
    async def _send_progress_update(self, checkpoint: ProgressCheckpoint) -> None:
        """Send progress update via message bus.
        
        Args:
            checkpoint: The progress checkpoint.
        """
        if not self.bus:
            return
        
        msg = InboundMessage(
            channel="system",
            sender_id="progress_tracker",
            chat_id=self.task_id,
            content="",
            metadata={
                "type": "subagent_progress",
                "task_id": self.task_id,
                "stage": checkpoint.stage.value,
                "progress": checkpoint.progress,
                "message": checkpoint.message,
                "artifacts": checkpoint.artifacts,
            },
        )
        
        try:
            await self.bus.publish_inbound(msg)
        except Exception as e:
            logger.warning(f"Failed to send progress update: {e}")
    
    @staticmethod
    def _get_stage_name(stage: ProgressStage) -> str:
        """Get Chinese name for a stage.
        
        Args:
            stage: The progress stage.
            
        Returns:
            Chinese name for the stage.
        """
        names = {
            ProgressStage.INITIALIZING: "初始化",
            ProgressStage.ANALYZING: "分析",
            ProgressStage.EXECUTING: "执行",
            ProgressStage.VERIFYING: "验证",
            ProgressStage.FINALIZING: "收尾",
            ProgressStage.COMPLETED: "完成",
            ProgressStage.FAILED: "失败",
        }
        return names.get(stage, stage.value)
