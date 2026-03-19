"""Predefined Script Browser Automation - User defines scripts, AI orchestrates execution."""

import asyncio
import json
import re
import ast
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from loguru import logger

from nanobot.agent.tools.base import Tool
from nanobot.utils.helpers import get_data_path, ensure_dir, safe_filename


class BrowserMode(str, Enum):
    HEADLESS = "headless"
    HEADED = "headed"
    DEBUG = "debug"


class StepType(str, Enum):
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    SELECT = "select"
    CHECK = "check"
    HOVER = "hover"
    PRESS = "press"


@dataclass
class JSONScriptStep:
    id: str
    step_type: str
    selector: str = ""
    selector_type: str = "css"
    value: str = ""
    param_binding: Optional[str] = None
    description: str = ""
    wait_after: int = 0
    timeout: int = 15000
    screenshot: Optional[str] = None
    extract_type: str = "text"
    extract_attr: Optional[str] = None
    result_name: Optional[str] = None
    result_binding: Optional[str] = None
    multiple: bool = False
    wait_for_element: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "JSONScriptStep":
        return cls(
            id=str(data.get("id", "")),
            step_type=data.get("step_type", ""),
            selector=data.get("selector", ""),
            selector_type=data.get("selector_type", "css"),
            value=data.get("value", ""),
            param_binding=data.get("param_binding"),
            description=data.get("description", ""),
            wait_after=data.get("wait_after", 0),
            timeout=data.get("timeout", 15000),
            screenshot=data.get("screenshot"),
            extract_type=data.get("extract_type", "text"),
            extract_attr=data.get("extract_attr"),
            result_name=data.get("result_name"),
            result_binding=data.get("result_binding"),
            multiple=data.get("multiple", False),
            wait_for_element=data.get("wait_for_element", True),
        )


@dataclass
class JSONScriptParam:
    name: str
    type: str = "string"
    required: bool = True
    default: Any = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "JSONScriptParam":
        if isinstance(data, str):
            return cls(name=data)
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "string"),
            required=data.get("required", True),
            default=data.get("default"),
            description=data.get("description", ""),
        )


@dataclass
class JSONScriptReturn:
    name: str
    description: str = ""
    return_type: str = "any"

    @classmethod
    def from_dict(cls, data: dict) -> "JSONScriptReturn":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            return_type=data.get("return_type", "any"),
        )


@dataclass
class JSONScriptMeta:
    file: str
    name: str
    description: str = ""
    category: str = "general"
    keywords: list[str] = field(default_factory=list)
    params: list[JSONScriptParam] = field(default_factory=list)
    returns: list[JSONScriptReturn] = field(default_factory=list)
    steps: list[JSONScriptStep] = field(default_factory=list)
    version: str = "1.0"

    @classmethod
    def from_dict(cls, data: dict, filename: str) -> "JSONScriptMeta":
        params = [JSONScriptParam.from_dict(p) for p in data.get("params", [])]
        returns = [JSONScriptReturn.from_dict(r) for r in data.get("returns", [])]
        steps = [JSONScriptStep.from_dict(s) for s in data.get("steps", [])]
        keywords = data.get("keywords", "")
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        
        return cls(
            file=filename,
            name=data.get("name", filename.replace(".json", "")),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            keywords=keywords,
            params=params,
            returns=returns,
            steps=steps,
            version=data.get("version", "1.0"),
        )

    def to_script_meta(self) -> "ScriptMeta":
        return ScriptMeta(
            file=self.file,
            name=self.name,
            description=self.description,
            params=[
                ScriptParam(
                    name=p.name,
                    description=p.description,
                    required=p.required,
                    default=p.default,
                    type=p.type,
                )
                for p in self.params
            ],
            returns=[
                ScriptReturn(name=r.name, description=r.description, type=r.return_type)
                for r in self.returns
            ],
            keywords=self.keywords,
            dependencies=[],
            examples=[],
            category=self.category,
        )


@dataclass
class ScriptParam:
    name: str
    description: str = ""
    required: bool = True
    default: Any = None
    type: str = "string"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "type": self.type,
        }


@dataclass
class ScriptReturn:
    name: str
    description: str = ""
    type: str = "any"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
        }


@dataclass
class ScriptMeta:
    file: str
    name: str
    description: str
    params: list[ScriptParam]
    returns: list[ScriptReturn]
    keywords: list[str]
    dependencies: list[str]
    examples: list[str]
    category: str = "general"

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "name": self.name,
            "description": self.description,
            "params": [p.to_dict() for p in self.params],
            "returns": [r.to_dict() for r in self.returns],
            "keywords": self.keywords,
            "dependencies": self.dependencies,
            "examples": self.examples,
            "category": self.category,
        }


@dataclass
class ExecutionResult:
    success: bool
    data: dict
    message: str
    script_name: str
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "script_name": self.script_name,
            "duration_ms": self.duration_ms,
        }


class ScriptParser:
    @staticmethod
    def parse_script_metadata(file_path: Path) -> Optional[ScriptMeta]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ScriptParser._parse_docstring(content, file_path.name)
        except Exception as e:
            logger.error(f"Parse script error {file_path}: {e}")
            return None

    @staticmethod
    def _parse_docstring(content: str, filename: str) -> ScriptMeta:
        meta = ScriptMeta(
            file=filename,
            name=filename.replace(".py", "").replace("_", " ").title(),
            description="",
            params=[],
            returns=[],
            keywords=[],
            dependencies=[],
            examples=[],
        )
        doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if not doc_match:
            doc_match = re.search(r"'''(.*?)'''", content, re.DOTALL)
        if not doc_match:
            return meta
        docstring = doc_match.group(1).strip()
        lines = docstring.split("\n")
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("@name:"):
                meta.name = line[6:].strip()
            elif line.startswith("@description:"):
                meta.description = line[13:].strip()
            elif line.startswith("@category:"):
                meta.category = line[10:].strip()
            elif line.startswith("@params:"):
                current_section = "params"
            elif line.startswith("@returns:"):
                current_section = "returns"
            elif line.startswith("@keywords:"):
                meta.keywords = [k.strip() for k in line[10:].split(",")]
            elif line.startswith("@dependencies:"):
                meta.dependencies = [d.strip() for d in line[14:].split(",")]
            elif line.startswith("@examples:"):
                current_section = "examples"
            elif line.startswith("-") or line.startswith("  -"):
                item = line.lstrip("- ").strip()
                if current_section == "params":
                    param = ScriptParser._parse_param_line(item)
                    if param:
                        meta.params.append(param)
                elif current_section == "returns":
                    ret = ScriptParser._parse_return_line(item)
                    if ret:
                        meta.returns.append(ret)
                elif current_section == "examples":
                    meta.examples.append(item)
        return meta

    @staticmethod
    def _parse_param_line(line: str) -> Optional[ScriptParam]:
        parts = line.split(":", 1)
        if len(parts) < 2:
            return None
        name = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        required = not name.endswith("?")
        name = name.rstrip("?")
        param_type = "string"
        default = None
        type_match = re.search(r"\((\w+)\)", rest)
        if type_match:
            param_type = type_match.group(1)
        default_match = re.search(r"\[default:\s*([^\]]+)\]", rest)
        if default_match:
            default = default_match.group(1)
            try:
                if param_type == "int":
                    default = int(default)
                elif param_type == "float":
                    default = float(default)
                elif param_type == "bool":
                    default = default.lower() == "true"
            except Exception:
                pass
        description = re.sub(r"\([^)]*\)", "", rest).replace(f"[default: {default}]", "").strip()
        return ScriptParam(
            name=name,
            description=description,
            required=required,
            default=default,
            type=param_type,
        )

    @staticmethod
    def _parse_return_line(line: str) -> Optional[ScriptReturn]:
        parts = line.split(":", 1)
        if len(parts) < 2:
            return None
        name = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        ret_type = "any"
        type_match = re.search(r"\((\w+)\)", rest)
        if type_match:
            ret_type = type_match.group(1)
        description = re.sub(r"\([^)]*\)", "", rest).strip()
        return ScriptReturn(name=name, description=description, type=ret_type)


class ScriptExecutor:
    def __init__(self, scripts_dir: Path):
        self.scripts_dir = scripts_dir
        self.scripts: dict[str, ScriptMeta] = {}
        self.json_scripts: dict[str, JSONScriptMeta] = {}
        self._browser_session = None
        self._load_scripts()

        self._load_json_scripts()

    def _load_scripts(self):
        if not self.scripts_dir.exists():
            return
        for f in self.scripts_dir.glob("*.py"):
            if f.name.startswith("_"):
                continue
            meta = ScriptParser.parse_script_metadata(f)
            if meta:
                self.scripts[meta.name] = meta
                self.scripts[meta.file] = meta

    def _load_json_scripts(self):
        if not self.scripts_dir.exists():
            return
        for f in self.scripts_dir.glob("*.json"):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as file:
                    content = json.load(file)
                if isinstance(content, list):
                    for item in content:
                        json_meta = JSONScriptMeta.from_dict(item, f.name)
                        self.json_scripts[json_meta.name] = json_meta
                        self.json_scripts[json_meta.file] = json_meta
                        script_meta = json_meta.to_script_meta()
                        self.scripts[script_meta.name] = script_meta
                        self.scripts[script_meta.file] = script_meta
                elif isinstance(content, dict):
                    json_meta = JSONScriptMeta.from_dict(content, f.name)
                    self.json_scripts[json_meta.name] = json_meta
                    self.json_scripts[json_meta.file] = json_meta
                    script_meta = json_meta.to_script_meta()
                    self.scripts[script_meta.name] = script_meta
                    self.scripts[script_meta.file] = script_meta
            except Exception as e:
                logger.error(f"Load JSON script error {f}: {e}")

    def reload_scripts(self):
        self.scripts.clear()
        self.json_scripts.clear()
        self._load_scripts()
        self._load_json_scripts()

    def get_script(self, name: str) -> Optional[ScriptMeta]:
        return self.scripts.get(name)

    def list_scripts(self) -> list[ScriptMeta]:
        seen = set()
        result = []
        for meta in self.scripts.values():
            if meta.name not in seen:
                seen.add(meta.name)
                result.append(meta)
        return result

    async def execute(
        self,
        script_name: str,
        params: dict[str, Any],
        page=None,
        mode: BrowserMode = BrowserMode.HEADED,
    ) -> ExecutionResult:
        json_meta = self.json_scripts.get(script_name)
        if json_meta:
            return await self._execute_json_script(json_meta, params, page, mode)
        script_meta = self.get_script(script_name)
        if not script_meta:
            return ExecutionResult(
                success=False,
                data={},
                message=f"Script '{script_name}' not found",
                script_name=script_name,
            )
        missing_params = []
        for p in script_meta.params:
            if p.required and p.name not in params and p.default is None:
                missing_params.append(p.name)
        if missing_params:
            return ExecutionResult(
                success=False,
                data={},
                message=f"Missing required parameters: {', '.join(missing_params)}",
                script_name=script_name,
            )
        merged_params = {}
        for p in script_meta.params:
            if p.name in params:
                merged_params[p.name] = params[p.name]
            elif p.default is not None:
                merged_params[p.name] = p.default
        start_time = datetime.now()
        try:
            script_path = self.scripts_dir / script_meta.file
            with open(script_path, "r", encoding="utf-8") as f:
                script_code = f.read()
            local_vars = {"page": page, "params": merged_params, "result": None}
            exec(script_code, local_vars)
            execute_func = local_vars.get("execute")
            if not execute_func:
                return ExecutionResult(
                    success=False,
                    data={},
                    message="Script must define an 'execute' function",
                    script_name=script_name,
                )
            result = await execute_func(page, **merged_params)
            if result is None:
                result = {"success": True}
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=result.get("success", True),
                data=result,
                message=result.get("message", "Execution completed"),
                script_name=script_name,
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=False,
                data={},
                message=f"Execution error: {str(e)}",
                script_name=script_name,
                duration_ms=duration,
            )

    async def _execute_json_script(
        self,
        json_meta: JSONScriptMeta,
        params: dict[str, Any],
        page,
        mode: BrowserMode,
    ) -> ExecutionResult:
        start_time = datetime.now()
        try:
            context = {"page": page, "params": params, "results": {}, "screenshots": {}}
            for p in json_meta.params:
                if p.required and p.name not in params and p.default is None:
                    return ExecutionResult(
                        success=False,
                        data={},
                        message=f"Missing required parameter: {p.name}",
                        script_name=json_meta.name,
                        duration_ms=0,
                    )
            for p in json_meta.params:
                if p.name in params:
                    context["params"][p.name] = params[p.name]
                elif p.default is not None:
                    context["params"][p.name] = p.default
            for step in json_meta.steps:
                try:
                    result = await self._execute_step(step, context)
                    if result:
                        context["results"][step.result_name or f"step_{step.id}"] = result
                except Exception as e:
                    duration = int((datetime.now() - start_time).total_seconds() * 1000)
                    return ExecutionResult(
                        success=False,
                        data={},
                        message=f"Step {step.id} ({step.step_type}) failed: {str(e)}",
                        script_name=json_meta.name,
                        duration_ms=duration,
                    )
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=True,
                data=context.get("results", {}),
                message=f"Executed {len(json_meta.steps)} steps successfully",
                script_name=json_meta.name,
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=False,
                data={},
                message=f"JSON script execution error: {str(e)}",
                script_name=json_meta.name,
                duration_ms=duration,
            )

    async def _execute_step(self, step: JSONScriptStep, context: dict) -> Any:
        page = context.get("page")
        if not page:
            return "No page available"
        try:
            if step.wait_for_element and step.selector:
                try:
                    await page.wait_for_selector(step.selector, timeout=step.timeout)
                except Exception:
                    pass
            value = step.value
            if step.param_binding:
                value = context["params"].get(step.param_binding, value)
            if step.step_type == "goto":
                await page.goto(value, timeout=step.timeout)
            elif step.step_type == "click":
                await page.click(step.selector)
            elif step.step_type == "fill":
                await page.fill(step.selector, value)
            elif step.step_type == "select":
                await page.select_option(step.selector, value)
            elif step.step_type == "check":
                await page.check(step.selector)
            elif step.step_type == "hover":
                await page.hover(step.selector)
            elif step.step_type == "press":
                await page.press(step.selector, value)
            elif step.step_type == "wait":
                await page.wait_for_timeout(step.timeout)
            elif step.step_type == "screenshot":
                screenshot_path = step.screenshot or f"screenshot_{step.id}.png"
                await page.screenshot(path=screenshot_path)
                context["screenshots"][step.id] = screenshot_path
            elif step.step_type == "extract":
                elements = await page.query_selector_all(step.selector) if step.multiple else [await page.query_selector(step.selector)]
                elements = [el for el in elements if el is not None]
                if not elements:
                    return None
                if step.extract_type == "text":
                    if step.multiple:
                        results = []
                        for el in elements:
                            text = await el.text_content()
                            results.append(text.strip() if text else "")
                        return results
                    else:
                        text = await elements[0].text_content()
                        return text.strip() if text else None
                elif step.extract_type == "html":
                    if step.multiple:
                        results = []
                        for el in elements:
                            html = await el.inner_html()
                            results.append(html)
                        return results
                    else:
                        return await elements[0].inner_html()
                elif step.extract_type == "attr":
                    attr_name = step.extract_attr or "href"
                    if step.multiple:
                        results = []
                        for el in elements:
                            attr = await el.get_attribute(attr_name)
                            results.append(attr)
                        return results
                    else:
                        return await elements[0].get_attribute(attr_name)
                else:
                    return None
            else:
                return None
        except Exception as e:
            logger.error(f"Step {step.id} execution error: {e}")
            return f"Error: {str(e)}"


class BrowserSession:
    _browser_installed = False

    def __init__(self, mode: BrowserMode = BrowserMode.HEADED):
        self.mode = mode
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    @classmethod
    def _ensure_browser_installed(cls) -> tuple[bool, str]:
        if cls._browser_installed:
            return True, "OK"
        import subprocess
        import sys
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                cls._browser_installed = True
                return True, "OK"
            return False, result.stderr[:200] if result.stderr else "Install failed"
        except Exception as e:
            return False, str(e)

    async def start(self) -> tuple[bool, str]:
        try:
            from playwright.async_api import async_playwright, Error as PlaywrightError
        except ImportError:
            return False, "Playwright not installed. Run: pip install playwright"
        try:
            if not self._browser_installed:
                loop = asyncio.get_event_loop()
                ok, msg = await loop.run_in_executor(None, self._ensure_browser_installed)
                if not ok:
                    return False, msg
            self.playwright = await async_playwright().start()
            launch_opts = {"headless": self.mode == BrowserMode.HEADLESS}
            if self.mode == BrowserMode.DEBUG:
                launch_opts["slow_mo"] = 300
            self.browser = await self.playwright.chromium.launch(**launch_opts)
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="zh-CN",
            )
            self.page = await self.context.new_page()
            if self.mode in (BrowserMode.HEADED, BrowserMode.DEBUG):
                await self.page.bring_to_front()
            return True, "OK"
        except PlaywrightError as e:
            return False, str(e)[:200]
        except Exception as e:
            return False, str(e)

    async def close(self):
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.page = self.context = self.browser = self.playwright = None


class IntentMatcher:
    def __init__(self, scripts: dict[str, ScriptMeta]):
        self.scripts = scripts

    def match(self, intent: str) -> list[tuple[ScriptMeta, float]]:
        intent_lower = intent.lower()
        scores = []
        for meta in self.scripts.values():
            if meta.name in [s[0].name for s in scores]:
                continue
            score = 0.0
            for kw in meta.keywords:
                if kw.lower() in intent_lower:
                    score += 2.0
            if meta.name.lower() in intent_lower:
                score += 3.0
            for word in meta.name.lower().split():
                if word in intent_lower:
                    score += 1.0
            if meta.description:
                for word in meta.description.lower().split():
                    if len(word) > 2 and word in intent_lower:
                        score += 0.5
            if score > 0:
                scores.append((meta, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:3]

    def extract_params(self, intent: str, script_meta: ScriptMeta) -> dict[str, Any]:
        params = {}
        intent_lower = intent.lower()
        for param in script_meta.params:
            if param.name in ["username", "user", "账号", "用户名"]:
                match = re.search(
                    r"(?:用户名|账号|username|user)[：:]\s*([^\s,，]+)",
                    intent,
                    re.IGNORECASE,
                )
                if match:
                    params[param.name] = match.group(1)
            elif param.name in ["password", "密码"]:
                match = re.search(r"(?:密码|password)[：:]\s*([^\s,，]+)", intent, re.IGNORECASE)
                if match:
                    params[param.name] = match.group(1)
            elif param.name in ["date", "日期"]:
                if "今天" in intent or "今日" in intent:
                    params[param.name] = datetime.now().strftime("%Y-%m-%d")
                elif "昨天" in intent or "昨日" in intent:
                    params[param.name] = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                elif "上个月" in intent or "上月" in intent:
                    first = datetime.now().replace(day=1) - timedelta(days=1)
                    params[param.name] = first.strftime("%Y-%m")
            elif param.name in ["start_date", "开始日期", "起始日期"]:
                if "上个月" in intent or "上月" in intent:
                    first = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
                    params[param.name] = first.strftime("%Y-%m-%d")
            elif param.name in ["end_date", "结束日期", "截止日期"]:
                if "上个月" in intent or "上月" in intent:
                    last = datetime.now().replace(day=1) - timedelta(days=1)
                    params[param.name] = last.strftime("%Y-%m-%d")
            elif param.type == "int":
                match = re.search(rf"{param.name}[：:]\s*(\d+)", intent, re.IGNORECASE)
                if match:
                    params[param.name] = int(match.group(1))
            elif param.type == "string":
                match = re.search(rf"{param.name}[：:]\s*([^\s,，]+)", intent, re.IGNORECASE)
                if match:
                    params[param.name] = match.group(1)
        return params


class BrowserTool(Tool):
    name = "browser"
    description = """浏览器脚本执行器 - 用户定义JSON脚本，AI调度执行

## 支持的脚本格式

- JSON 脚本 (.json): 声明式配置，易于生成和编辑
- Python 脚本 (.py): 灵活强大，支持复杂逻辑

## 工作方式

1. 用户在 scripts/ 目录下编写自动化脚本（.json 或 .py）
2. 脚本声明参数、返回值、关键词等元数据
3. AI 根据用户意图匹配并调用脚本
4. 脚本执行并返回结果给 AI

## 可用操作

- run: 执行指定脚本
- list: 列出所有可用脚本
- info: 查看脚本详情
- reload: 重新加载脚本
- create: 创建脚本模板
- close: 关闭浏览器

## 使用示例

用户: "帮我登录CRM系统"
AI: 匹配到 crm 脚本，执行登录流程...

用户: "查询异常工时记录"
AI: 匹配到 crm 脚本，执行查询操作...

用户: "导出数据到Excel"
AI: 匹配到 export_data 脚本，执行导出..."""

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["run", "list", "info", "reload", "create", "close"],
            },
            "script_name": {"type": "string", "description": "脚本名称"},
            "intent": {"type": "string", "description": "用户意图描述"},
            "params": {"type": "object", "description": "脚本参数"},
            "mode": {"type": "string", "enum": ["headless", "headed", "debug"]},
        },
        "required": ["action"],
    }

    def __init__(self):
        self._scripts_dir = ensure_dir(get_data_path() / "browser" / "scripts")
        self._executor = ScriptExecutor(self._scripts_dir)
        self._session: Optional[BrowserSession] = None
        self._llm_callback: Optional[Callable] = None
        self._matcher = IntentMatcher(self._executor.scripts)

    def set_llm_callback(self, callback: Callable):
        self._llm_callback = callback

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        try:
            if action == "run":
                return await self._run_script(kwargs)
            elif action == "list":
                return self._list_scripts()
            elif action == "info":
                return self._script_info(kwargs)
            elif action == "reload":
                return self._reload_scripts()
            elif action == "create":
                return self._create_template(kwargs)
            elif action == "close":
                return await self._close_browser()
            return f"Unknown action: {action}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def _ensure_session(self, mode: BrowserMode = BrowserMode.HEADED) -> BrowserSession:
        if self._session and self._session.page:
            return self._session
        self._session = BrowserSession(mode=mode)
        ok, msg = await self._session.start()
        if not ok:
            raise RuntimeError(msg)
        return self._session

    async def _run_script(self, kwargs: dict) -> str:
        script_name = kwargs.get("script_name", "")
        intent = kwargs.get("intent", "")
        params = kwargs.get("params", {})
        mode_str = kwargs.get("mode", "headed")
        mode = BrowserMode(mode_str) if mode_str in ["headless", "headed", "debug"] else BrowserMode.HEADED

        if not script_name and intent:
            matches = self._matcher.match(intent)
            if matches:
                script_name = matches[0][0].name
                params.update(self._matcher.extract_params(intent, matches[0][0]))

        if not script_name:
            scripts = self._executor.list_scripts()
            if scripts:
                return f"请指定脚本名。可用: {', '.join(s.name for s in scripts)}"
            return "没有可用的脚本。请先在 scripts/ 目录下创建脚本。"

        script_meta = self._executor.get_script(script_name)
        if not script_meta:
            return f"脚本「{script_name}」不存在"

        missing = [p.name for p in script_meta.params if p.required and p.name not in params and p.default is None]
        if missing:
            return f"脚本「{script_name}」缺少必需参数: {', '.join(missing)}"

        try:
            session = await self._ensure_session(mode)
        except RuntimeError as e:
            return f"❌ 无法启动浏览器: {str(e)}"

        result = await self._executor.execute(script_name, params, session.page, mode)

        lines = [f"🚀 **执行脚本: {script_name}**\n"]
        if params:
            lines.append("**参数:**")
            for k, v in params.items():
                display = "***" if "password" in k.lower() or "密码" in k else str(v)[:30]
                lines.append(f"  • {k}: {display}")
            lines.append("")

        if result.success:
            lines.append(f"✅ **成功** ({result.duration_ms}ms)")
            if result.data:
                for k, v in result.data.items():
                    if k != "success" and k != "message":
                        val_str = str(v)[:200] if isinstance(v, (str, int, float)) else json.dumps(v, ensure_ascii=False)[:200]
                        lines.append(f"  • {k}: {val_str}")
        else:
            lines.append(f"❌ **失败**: {result.message}")

        return "\n".join(lines)

    def _list_scripts(self) -> str:
        scripts = self._executor.list_scripts()
        if not scripts:
            return "没有可用的脚本。\n\n在 scripts/ 目录下创建 .py 脚本文件，使用注释声明能力。"
        lines = ["📚 **可用脚本**\n"]
        by_category = {}
        for s in scripts:
            cat = s.category or "general"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(s)
        for cat, items in by_category.items():
            lines.append(f"**{cat}**")
            for s in items:
                param_str = ", ".join(p.name for p in s.params[:3])
                if len(s.params) > 3:
                    param_str += "..."
                lines.append(f"  • **{s.name}** - {s.description[:40]}")
                if param_str:
                    lines.append(f"    参数: {param_str}")
            lines.append("")
        lines.append("💡 说「执行 脚本名」或描述你的意图让 AI 匹配脚本")
        return "\n".join(lines)

    def _script_info(self, kwargs: dict) -> str:
        name = kwargs.get("script_name", "")
        if not name:
            scripts = self._executor.list_scripts()
            if scripts:
                return f"请指定脚本名。可用: {', '.join(s.name for s in scripts)}"
            return "没有可用的脚本"
        meta = self._executor.get_script(name)
        if not meta:
            return f"脚本「{name}」不存在"
        lines = [f"📜 **脚本: {meta.name}**\n"]
        lines.append(f"📁 文件: {meta.file}")
        lines.append(f"📝 描述: {meta.description}")
        lines.append(f"🏷️ 分类: {meta.category}")
        if meta.params:
            lines.append(f"\n**参数:**")
            for p in meta.params:
                req = "必需" if p.required else "可选"
                default = f" [默认: {p.default}]" if p.default is not None else ""
                lines.append(f"  • {p.name} ({p.type}, {req}){default}")
                if p.description:
                    lines.append(f"    {p.description}")
        if meta.returns:
            lines.append(f"\n**返回值:**")
            for r in meta.returns:
                lines.append(f"  • {r.name} ({r.type})")
                if r.description:
                    lines.append(f"    {r.description}")
        if meta.keywords:
            lines.append(f"\n**关键词:** {', '.join(meta.keywords)}")
        if meta.dependencies:
            lines.append(f"\n**依赖:** {', '.join(meta.dependencies)}")
        if meta.examples:
            lines.append(f"\n**示例:**")
            for ex in meta.examples:
                lines.append(f"  • {ex}")
        return "\n".join(lines)

    def _reload_scripts(self) -> str:
        self._executor.reload_scripts()
        self._matcher = IntentMatcher(self._executor.scripts)
        count = len(self._executor.list_scripts())
        return f"✅ 已重新加载，共 {count} 个脚本"

    def _create_template(self, kwargs: dict) -> str:
        name = kwargs.get("script_name", "new_script")
        filename = safe_filename(name) + ".py"
        filepath = self._scripts_dir / filename
        if filepath.exists():
            return f"脚本文件 {filename} 已存在"
        template = '''"""
@name: {name}
@description: 脚本功能描述
@category: general

@params:
  - param1: 参数1说明
  - param2?: 可选参数说明

@returns:
  - success: 是否成功
  - data: 返回数据

@keywords: 关键词1, 关键词2

@examples:
  - 示例1说明
"""
from playwright.async_api import async_playwright


async def execute(page, **params):
    """
    脚本主函数
    
    Args:
        page: Playwright page 对象
        **params: 脚本参数
        
    Returns:
        dict: 包含 success, message, data 等字段
    """
    param1 = params.get('param1', '')
    
    # TODO: 实现你的自动化逻辑
    await page.goto('https://example.com')
    
    # 返回结果
    return {{
        'success': True,
        'message': '执行成功',
        'data': {{}}
    }}
'''
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(template.format(name=name))
        self._executor.reload_scripts()
        return f"✅ 已创建脚本模板: {filename}\n📝 请编辑文件添加你的自动化逻辑"

    async def _close_browser(self) -> str:
        if self._session:
            await self._session.close()
            self._session = None
            return "✅ 浏览器已关闭"
        return "浏览器未打开"


class BrowserScriptTool(Tool):
    name = "browser_script"
    description = "Execute predefined browser automation scripts."
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["run", "list", "info", "reload", "create"]},
            "script_name": {"type": "string"},
            "intent": {"type": "string"},
            "params": {"type": "object"},
            "mode": {"type": "string", "enum": ["headless", "headed", "debug"]},
        },
        "required": ["action"],
    }

    def __init__(self, browser_tool: BrowserTool):
        self._bt = browser_tool

    async def execute(self, **kwargs) -> str:
        return await self._bt.execute(**kwargs)
