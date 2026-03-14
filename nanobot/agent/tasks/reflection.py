from dataclasses import dataclass
from typing import Any
from loguru import logger
import asyncio


@dataclass
class ReflectionConfig:
    enabled: bool = False
    max_retries: int = 2
    retry_delay: float = 3.0
    triggers_on_tool_error: bool = True
    triggers_on_complex_task: bool = True
    complexity_threshold: int = 3


class ReflectionManager:
    def __init__(self, config: ReflectionConfig | None = None):
        self.config = config or ReflectionConfig()

    async def handle_tool_error(
        self,
        tool_name: str,
        error: str,
        context: dict,
        executor_func,
    ) -> Any:
        if not self.config.enabled or not self.config.triggers_on_tool_error:
            raise Exception(error)

        last_error = error
        for attempt in range(self.config.max_retries):
            logger.info(f"Retrying tool {tool_name}, attempt {attempt + 1}")

            await asyncio.sleep(self.config.retry_delay)

            try:
                result = await executor_func()
                logger.info(f"Tool {tool_name} succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool {tool_name} failed: {e}")

        raise Exception(f"Tool {tool_name} failed after {self.config.max_retries} retries: {last_error}")

    async def verify_result(
        self,
        result: Any,
        expectations: dict,
        provider: Any,
        model: str
    ) -> tuple[bool, str]:
        if not self.config.enabled:
            return True, ""

        prompt = f"""验证以下结果是否符合预期：

结果: {result}

预期:
{chr(10).join(f"- {k}: {v}" for k, v in expectations.items())}

请返回JSON格式的验证结果：
{{
    "passed": true/false,
    "feedback": "如果未通过，说明原因和改进建议"
}}"""

        try:
            response = await provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=model,
            )

            import json
            content = response.content
            if "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                result_data = json.loads(content[start:end])
                return result_data.get("passed", True), result_data.get("feedback", "")
        except Exception as e:
            logger.warning(f"Result verification failed: {e}")

        return True, ""

    def should_reflect_on_task(self, task_complexity: int) -> bool:
        if not self.config.enabled or not self.config.triggers_on_complex_task:
            return False
        return task_complexity >= self.config.complexity_threshold

    def is_enabled(self) -> bool:
        return self.config.enabled

    def enable(self) -> None:
        self.config.enabled = True

    def disable(self) -> None:
        self.config.enabled = False
