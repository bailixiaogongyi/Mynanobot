"""Skills API routes for Web UI.

This module provides skill viewing API endpoints for the Web UI.
Skills are read-only - they cannot be created or edited through the Web UI.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

router = APIRouter()


class SkillMeta(BaseModel):
    """Skill metadata from frontmatter."""

    name: str = ""
    description: str = ""
    always: bool = False


class SkillInfo(BaseModel):
    """Skill information."""

    name: str
    source: str
    path: str
    meta: SkillMeta
    available: bool = True


class SkillDetail(BaseModel):
    """Full skill detail including content."""

    name: str
    source: str
    path: str
    meta: SkillMeta
    content: str
    available: bool = True


def _get_workspace(request) -> Path:
    """Get workspace path from app state."""
    return request.app.state.config.workspace_path


def _get_registry_file(request) -> Path:
    """Get registry metadata file path."""
    workspace = _get_workspace(request)
    return workspace / ".registry.json"


def _get_installed_from_marketplace(request) -> dict[str, str]:
    """Get set of skill names installed from marketplace.

    Returns:
        Dict mapping skill_name -> "marketplace"
    """
    import json

    registry_file = _get_registry_file(request)
    if not registry_file.exists():
        return {}

    try:
        with open(registry_file, encoding="utf-8") as f:
            registry = json.load(f)
        return {meta.get("skillName"): "marketplace" for meta in registry.values() if meta.get("skillName")}
    except Exception as e:
        logger.error(f"Error reading registry: {e}")
        return {}


def _get_builtin_skills_dir() -> Path:
    """Get built-in skills directory."""
    return Path(__file__).parent.parent.parent / "skills"


def _parse_frontmatter(content: str) -> tuple[SkillMeta, str]:
    """Parse YAML frontmatter from skill content.

    Args:
        content: Raw skill file content.

    Returns:
        Tuple of (metadata, content_without_frontmatter).
    """
    meta = SkillMeta()

    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not frontmatter_match:
        return meta, content

    frontmatter = frontmatter_match.group(1)
    body = content[frontmatter_match.end() :]

    for line in frontmatter.split("\n"):
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")

        if key == "name":
            meta.name = value
        elif key == "description":
            meta.description = value
        elif key == "always":
            meta.always = value.lower() in ("true", "yes", "1")

    return meta, body


def _load_skill(skill_dir: Path, source: str) -> SkillInfo | None:
    """Load skill information from directory.

    Args:
        skill_dir: Path to skill directory.
        source: Source type (builtin or workspace).

    Returns:
        SkillInfo or None if not found.
    """
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(content)

        if not meta.name:
            meta.name = skill_dir.name

        return SkillInfo(
            name=skill_dir.name,
            source=source,
            path=str(skill_file),
            meta=meta,
        )
    except Exception as e:
        logger.error(f"Error loading skill {skill_dir}: {e}")
        return None


@router.get("/list", response_model=list[SkillInfo])
async def list_skills(
    request: Request,
    source: Optional[str] = Query(None, description="Filter by source: builtin, workspace, marketplace"),
) -> list[SkillInfo]:
    """List all available skills.

    Args:
        source: Optional filter by source type.

    Returns:
        List of skill information.
    """
    skills = []
    marketplace_skills = _get_installed_from_marketplace(request)

    if source is None or source == "workspace" or source == "marketplace":
        workspace = _get_workspace(request)
        workspace_skills_dir = workspace / "skills"

        if workspace_skills_dir.exists():
            for skill_dir in sorted(workspace_skills_dir.iterdir()):
                if skill_dir.is_dir():
                    skill_name = skill_dir.name
                    if skill_name.startswith("."):
                        continue
                    
                    skill_source = marketplace_skills.get(skill_name, "workspace")
                    
                    if source and source != skill_source:
                        continue
                    
                    skill_info = _load_skill(skill_dir, skill_source)
                    if skill_info:
                        skills.append(skill_info)

    if source is None or source == "builtin":
        builtin_skills_dir = _get_builtin_skills_dir()

        if builtin_skills_dir.exists():
            for skill_dir in sorted(builtin_skills_dir.iterdir()):
                if skill_dir.is_dir():
                    skill_info = _load_skill(skill_dir, "builtin")
                    if skill_info:
                        existing_names = [s.name for s in skills]
                        if skill_info.name not in existing_names:
                            skills.append(skill_info)

    return skills


@router.get("/sources")
async def list_sources() -> list[dict[str, str]]:
    """List available skill sources.

    Returns:
        List of source types.
    """
    return [
        {"id": "builtin", "name": "内置技能"},
        {"id": "marketplace", "name": "市场技能"},
        {"id": "workspace", "name": "自建技能"},
    ]


@router.get("/{skill_name}", response_model=SkillDetail)
async def get_skill(
    skill_name: str,
    request: Request,
    source: Optional[str] = Query(None, description="Source: builtin or workspace"),
) -> SkillDetail:
    """Get skill details by name.

    Args:
        skill_name: Skill name (directory name).
        source: Optional source filter.

    Returns:
        Full skill details including content.
    """
    workspace = _get_workspace(request)
    workspace_skills_dir = workspace / "skills"
    builtin_skills_dir = _get_builtin_skills_dir()

    search_order = []

    if source == "workspace":
        search_order = [(workspace_skills_dir, "workspace")]
    elif source == "builtin":
        search_order = [(builtin_skills_dir, "builtin")]
    elif source == "marketplace":
        search_order = [(workspace_skills_dir, "marketplace")]
    else:
        search_order = [
            (workspace_skills_dir, "workspace"),
            (builtin_skills_dir, "builtin"),
        ]

    # 获取市场技能注册表
    marketplace_skills = _get_installed_from_marketplace(request)
    
    for skills_dir, src in search_order:
        skill_file = skills_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            try:
                content = skill_file.read_text(encoding="utf-8")
                meta, body = _parse_frontmatter(content)

                if not meta.name:
                    meta.name = skill_name
                
                # 确定真实的技能来源
                actual_source = src
                if src == "workspace" and skill_name in marketplace_skills:
                    actual_source = "marketplace"

                return SkillDetail(
                    name=skill_name,
                    source=actual_source,
                    path=str(skill_file),
                    meta=meta,
                    content=body.strip(),
                )
            except Exception as e:
                logger.error(f"Error reading skill {skill_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Error reading skill: {e}")

    raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")
