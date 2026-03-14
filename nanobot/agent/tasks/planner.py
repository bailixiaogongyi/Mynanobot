from dataclasses import dataclass, field
from typing import Any
from loguru import logger
import json

from nanobot.agent.tasks.models import Task, TaskStatus, TaskPriority, TaskContext


@dataclass
class SubTask:
    id: str
    title: str
    description: str
    role: str | None = None
    depends_on: list[str] = field(default_factory=list)
    input_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskPlan:
    original_task: str
    complexity: str
    execution_strategy: str
    subtasks: list[SubTask] = field(default_factory=list)
    estimated_duration: int = 0


class TaskPlanner:
    def __init__(
        self,
        task_manager,
        role_manager,
        shared_context=None,
    ):
        self.task_manager = task_manager
        self.role_manager = role_manager
        self.shared_context = shared_context

    async def plan(
        self,
        task_description: str,
        provider: Any,
        model: str,
    ) -> TaskPlan:
        analysis = await self._analyze_task(task_description, provider, model)
        subtasks = self._decompose_task(analysis)
        for subtask in subtasks:
            subtask.role = self._allocate_agent(subtask)

        strategy = self._determine_strategy(subtasks)

        plan = TaskPlan(
            original_task=task_description,
            complexity=analysis.get("complexity", "normal"),
            subtasks=subtasks,
            execution_strategy=strategy,
        )

        logger.info(f"Generated plan: {len(subtasks)} subtasks, strategy: {strategy}")
        return plan

    async def _analyze_task(
        self,
        task: str,
        provider: Any,
        model: str
    ) -> dict:
        prompt = f"""分析以下任务，返回JSON格式的分析结果：

任务：{task}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
    "complexity": "simple/normal/complex",
    "estimated_steps": 数字,
    "required_roles": ["角色1", "角色2"],
    "dependencies": "任务依赖描述",
    "suggested_approach": "建议的处理方式"
}}"""

        response = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )

        try:
            content = response.content
            if "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                return json.loads(content[start:end])
        except Exception as e:
            logger.warning(f"Failed to parse task analysis: {e}")

        return {
            "complexity": "normal",
            "estimated_steps": 2,
            "required_roles": ["general_assistant"],
            "dependencies": "无",
            "suggested_approach": "直接执行"
        }

    def _decompose_task(self, analysis: dict) -> list[SubTask]:
        complexity = analysis.get("complexity", "normal")

        if complexity == "simple":
            return [SubTask(
                id="1",
                title=analysis.get("suggested_approach", "执行任务"),
                description=analysis.get("dependencies", ""),
            )]

        steps = analysis.get("estimated_steps", 3)
        subtasks = []

        for i in range(steps):
            subtasks.append(SubTask(
                id=str(i + 1),
                title=f"步骤 {i + 1}",
                description=f"任务步骤 {i + 1}",
            ))

        for i in range(1, len(subtasks)):
            subtasks[i].depends_on = [subtasks[i-1].id]

        return subtasks

    def _allocate_agent(self, subtask: SubTask) -> str:
        title = subtask.title.lower()

        if any(kw in title for kw in ["代码", "开发", "编程", "code", "写代码"]):
            return "code_developer"
        if any(kw in title for kw in ["文档", "文档编写", "报告", "写", "总结"]):
            return "document_writer"
        if any(kw in title for kw in ["研究", "调研", "分析", "查找", "搜索"]):
            return "researcher"
        if any(kw in title for kw in ["数据", "分析", "统计", "处理"]):
            return "data_analyst"

        return "general_assistant"

    def _determine_strategy(self, subtasks: list[SubTask]) -> str:
        if not subtasks:
            return "sequential"

        has_deps = any(st.depends_on for st in subtasks)
        if has_deps:
            return "sequential"

        if len(subtasks) > 1:
            return "parallel"

        return "sequential"

    async def execute_plan(
        self,
        plan: TaskPlan,
        origin_channel: str,
        origin_chat_id: str,
    ) -> list[Task]:
        created_tasks = []

        if plan.execution_strategy == "parallel":
            for subtask in plan.subtasks:
                if not subtask.depends_on:
                    task = self._create_subtask(
                        subtask,
                        plan.original_task,
                        origin_channel,
                        origin_chat_id
                    )
                    created_tasks.append(task)

        elif plan.execution_strategy == "sequential":
            for subtask in plan.subtasks:
                task = self._create_subtask(
                    subtask,
                    plan.original_task,
                    origin_channel,
                    origin_chat_id
                )
                created_tasks.append(task)

        return created_tasks

    def _create_subtask(
        self,
        subtask: SubTask,
        parent_task: str,
        origin_channel: str,
        origin_chat_id: str,
    ) -> Task:
        context = TaskContext(
            background=f"父任务: {parent_task}",
            requirements=[subtask.description],
        )

        return self.task_manager.create_task(
            title=subtask.title,
            description=subtask.description,
            context=context,
            role=subtask.role,
            priority=TaskPriority.MEDIUM,
            origin_channel=origin_channel,
            origin_chat_id=origin_chat_id,
        )
