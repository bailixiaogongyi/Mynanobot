"""Marketplace API routes for skill marketplace.

This module provides skill marketplace API endpoints including:
- Listing marketplace sources
- Browsing and searching skills
- Installing/updating/uninstalling skills
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Optional

import aiohttp
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# API endpoints
TENCENT_SEARCH_URL = "https://lightmake.site/api/skills"
TENCENT_DOWNLOAD_URL = "https://lightmake.site/api/v1/download"
TENCENT_INDEX_URL = "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills.json"

MAX_ARCHIVE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_JSON_BYTES = 1024 * 1024  # 1MB
DEFAULT_LIMIT = 24
MAX_LIMIT = 50


# ============== Pydantic Models ==============


class MarketplaceSource(BaseModel):
    """Marketplace source information."""

    id: str
    label: str
    description: str
    capabilities: dict[str, Any]


class MarketplaceSkill(BaseModel):
    """Marketplace skill item."""

    slug: str
    displayName: str
    summary: str
    latestVersion: Optional[str] = None
    installed: bool = False
    installedSkillName: Optional[str] = None
    installedVersion: Optional[str] = None
    hasUpdate: bool = False
    updatedAt: Optional[int] = None
    downloads: Optional[int] = None
    stars: Optional[int] = None
    installs: Optional[int] = None
    category: Optional[str] = None
    ownerName: Optional[str] = None
    url: Optional[str] = None


class MarketplaceDetail(MarketplaceSkill):
    """Full marketplace skill detail."""

    author: Optional[dict[str, Any]] = None
    moderation: Optional[dict[str, Any]] = None


class MarketplacePage(BaseModel):
    """Paginated marketplace skill list."""

    items: list[MarketplaceSkill]
    nextCursor: Optional[str] = None
    query: str
    sort: str
    order: str


class InstallRequest(BaseModel):
    """Skill installation request."""

    slug: str
    source: str = "tencent"


class UninstallRequest(BaseModel):
    """Skill uninstallation request."""

    slug: str


class UpdateRequest(BaseModel):
    """Skill update request."""

    slug: str
    source: str = "tencent"


class InstallResult(BaseModel):
    """Skill installation result."""

    success: bool
    skillName: str
    version: str
    message: str


class RegistryMeta(BaseModel):
    """Registry metadata for installed skill."""

    slug: str
    skillName: str
    source: str
    version: str
    installedAt: int


# ============== Helper Functions ==============


def _get_workspace(request: Request) -> Path:
    """Get workspace path from app state."""
    return request.app.state.config.workspace_path


def _get_skills_dir(request: Request) -> Path:
    """Get workspace skills directory."""
    workspace = _get_workspace(request)
    skills_dir = workspace / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


def _get_registry_file(request: Request) -> Path:
    """Get registry metadata file path."""
    workspace = _get_workspace(request)
    return workspace / ".registry.json"


def _load_registry(request: Request) -> dict[str, RegistryMeta]:
    """Load registry metadata."""
    registry_file = _get_registry_file(request)
    if registry_file.exists():
        try:
            data = json.loads(registry_file.read_text(encoding="utf-8"))
            return {k: RegistryMeta(**v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Failed to load registry: {e}")
    return {}


def _save_registry(request: Request, registry: dict[str, RegistryMeta]) -> None:
    """Save registry metadata."""
    registry_file = _get_registry_file(request)
    data = {k: v.model_dump() for k, v in registry.items()}
    registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_installed_skills(request: Request) -> dict[str, RegistryMeta]:
    """Get installed skills from registry."""
    return _load_registry(request)


async def _fetch_json(url: str, headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Fetch JSON from URL with retry logic."""
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 429 and attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if response.status != 200:
                        text = await response.text()
                        raise HTTPException(status_code=response.status, detail=f"Request failed: {text}")

                    text = await response.text()
                    if len(text) > MAX_JSON_BYTES:
                        raise HTTPException(status_code=500, detail="Response exceeds max size")

                    return json.loads(text)
            except aiohttp.ClientError as e:
                if attempt == 2:
                    raise HTTPException(status_code=500, detail=f"Network error: {e}")
                await asyncio.sleep(2 ** attempt)


async def _fetch_buffer(url: str, headers: Optional[dict[str, str]] = None, max_retries: int = 5) -> bytes:
    """Fetch binary buffer from URL with retry logic for 429 errors."""
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(max_retries):
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 429:
                        if attempt < max_retries - 1:
                            retry_after = response.headers.get("Retry-After", "3")
                            base_delay = int(retry_after) if retry_after.isdigit() else 3
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Rate limited (429), retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            text = await response.text()
                            raise HTTPException(status_code=429, detail=f"Rate limited: {text}")
                    
                    if response.status != 200:
                        text = await response.text()
                        raise HTTPException(status_code=response.status, detail=f"Download failed: {text}")

                    content_length = response.content_length
                    if content_length and content_length > MAX_ARCHIVE_BYTES:
                        raise HTTPException(status_code=500, detail="Archive exceeds max size")

                    buffer = await response.read()
                    if len(buffer) > MAX_ARCHIVE_BYTES:
                        raise HTTPException(status_code=500, detail="Archive exceeds max size")

                    return buffer
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"Network error: {e}")
                await asyncio.sleep(3 * (2 ** attempt))


def _extract_skill_from_zip(buffer: bytes, target_dir: Path) -> str:
    """Extract skill from ZIP buffer and return skill name."""
    with zipfile.ZipFile(io.BytesIO(buffer)) as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("Empty ZIP archive")

        skill_name = None
        root_folder = None
        
        # 首先查找包含 SKILL.md 的目录
        for name in names:
            if name.endswith("/SKILL.md") or name == "SKILL.md":
                parts = name.split("/")
                if len(parts) > 1:
                    # SKILL.md 在子目录中，使用该子目录名作为技能名
                    root_folder = parts[0]
                    skill_name = parts[0]
                else:
                    # SKILL.md 在根目录
                    # 尝试从 ZIP 文件名或其他方式推断技能名
                    # 先查找是否有 _meta.json 或其他元数据文件
                    meta_file = None
                    for n in names:
                        if n == "_meta.json" or n.endswith("/_meta.json"):
                            meta_file = n
                            break
                    
                    if meta_file:
                        meta_parts = meta_file.split("/")
                        if len(meta_parts) > 1:
                            skill_name = meta_parts[0]
                            root_folder = skill_name
                        else:
                            # _meta.json 在根目录，尝试从中读取技能名
                            try:
                                with zf.open(meta_file) as f:
                                    import json
                                    meta_data = json.load(f)
                                    if "name" in meta_data:
                                        skill_name = meta_data["name"]
                            except:
                                pass
                    
                    # 如果还是没有技能名，使用第一个非目录文件的基名
                    if not skill_name:
                        for name in names:
                            if not name.endswith("/") and name != "SKILL.md" and name != "_meta.json":
                                base_name = Path(name).stem
                                if base_name:
                                    skill_name = base_name
                                    break
                    
                    # 最后兜底
                    if not skill_name:
                        skill_name = "skill"
                    root_folder = None
                break
        
        # 如果没有找到 SKILL.md，使用第一个目录作为根目录
        if not skill_name:
            for name in names:
                parts = name.split("/")
                if len(parts) > 1 and parts[0]:
                    root_folder = parts[0]
                    skill_name = parts[0]
                    break
        
        # 如果还没有找到，使用默认值
        if not skill_name:
            skill_name = "skill"
            root_folder = None

        target_dir.mkdir(parents=True, exist_ok=True)
        skill_target_dir = target_dir / skill_name
        
        # 确保技能目录不存在，避免文件冲突
        if skill_target_dir.exists():
            # 生成唯一的目录名
            import time
            skill_name = f"{skill_name}_{int(time.time())}"
            skill_target_dir = target_dir / skill_name
        
        skill_target_dir.mkdir(parents=True, exist_ok=True)
        
        for name in names:
            if name.endswith("/"):
                continue
            
            relative_path = name
            if root_folder and name.startswith(root_folder + "/"):
                relative_path = name[len(root_folder) + 1:]
            
            if not relative_path:
                continue
                
            target_path = skill_target_dir / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with zf.open(name) as src, open(target_path, "wb") as dst:
                dst.write(src.read())

        return skill_name


# ============== Marketplace Sources ==============


MARKETPLACE_SOURCES = [
    MarketplaceSource(
        id="tencent",
        label="Tencent",
        description="Tencent Skill Hub",
        capabilities={
            "search": True,
            "list": True,
            "detail": True,
            "download": True,
            "update": True,
            "auth": "none",
            "sorts": ["score", "downloads", "stars", "installs"],
        },
    ),
    MarketplaceSource(
        id="recommended",
        label="Recommended",
        description="Recommended skills by nanobot",
        capabilities={
            "search": False,
            "list": True,
            "detail": True,
            "download": False,
            "update": False,
            "auth": "none",
            "sorts": ["name"],
        },
    ),
]


# Recommended skills (from Tencent)
RECOMMENDED_SKILLS = [
    {
        "slug": "agent-browser",
        "displayName": "Agent Browser",
        "summary": "智能浏览器代理",
        "category": "productivity",
    },
    {
        "slug": "self-improving-agent",
        "displayName": "Self-Improving Agent",
        "summary": "自我提升的智能代理",
        "category": "ai-tools",
    },
    {
        "slug": "humanizer",
        "displayName": "Humanizer",
        "summary": "人性化文本处理",
        "category": "text-tools",
    },
]


# ============== Tencent API ==============


async def _tencent_list_skills(limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    """List skills from Tencent."""
    return await _fetch_json(TENCENT_SEARCH_URL)


async def _tencent_search_skills(query: str, limit: int = MAX_LIMIT) -> dict[str, Any]:
    """Search skills on Tencent."""
    url = f"{TENCENT_SEARCH_URL}?keyword={query}"
    return await _fetch_json(url)


async def _tencent_download(slug: str) -> bytes:
    """Download skill ZIP from Tencent."""
    url = f"{TENCENT_DOWNLOAD_URL}?slug={slug}"
    return await _fetch_buffer(url)


def _adapt_tencent_list_item(item: dict[str, Any], installed: dict[str, RegistryMeta]) -> MarketplaceSkill:
    """Adapt Tencent list item to MarketplaceSkill."""
    slug = item.get("slug", "")
    registry_meta = installed.get(slug)

    return MarketplaceSkill(
        slug=slug,
        source="tencent",
        displayName=item.get("name") or item.get("displayName") or slug,
        summary=item.get("description") or item.get("description_zh") or "",
        latestVersion=item.get("version"),
        installed=registry_meta is not None,
        installedSkillName=registry_meta.skillName if registry_meta else None,
        installedVersion=registry_meta.version if registry_meta else None,
        hasUpdate=False,
        updatedAt=item.get("updated_at"),
        downloads=item.get("downloads"),
        stars=item.get("stars"),
        installs=item.get("installs"),
        category=item.get("category"),
        ownerName=item.get("ownerName"),
        url=item.get("homepage"),
    )


# ============== Recommended Skills ==============


def _adapt_recommended_item(item: dict[str, Any], installed: dict[str, RegistryMeta]) -> MarketplaceSkill:
    """Adapt recommended item to MarketplaceSkill."""
    slug = item.get("slug", "")
    registry_meta = installed.get(slug)

    return MarketplaceSkill(
        slug=slug,
        source="recommended",
        displayName=item.get("displayName") or item.get("name") or slug,
        summary=item.get("summary") or item.get("description") or "",
        latestVersion="1.0.0",  # Default version for recommended
        installed=registry_meta is not None,
        installedSkillName=registry_meta.skillName if registry_meta else None,
        installedVersion=registry_meta.version if registry_meta else None,
        hasUpdate=False,
        category=item.get("category"),
    )


# ============== API Routes ==============


@router.get("/sources", response_model=list[MarketplaceSource])
async def list_marketplace_sources():
    """Get list of available marketplace sources.

    Returns:
        List of marketplace sources with their capabilities.
    """
    return MARKETPLACE_SOURCES


@router.get("/list", response_model=MarketplacePage)
async def list_marketplace_skills(
    request: Request,
    source: str = Query("tencent", description="Marketplace source: tencent, recommended"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    sort: str = Query("downloads", description="Sort field"),
    order: str = Query("desc", description="Sort order: asc, desc"),
    query: str = Query("", description="Search query"),
):
    """Get list of skills from marketplace.

    Args:
        source: Marketplace source to query.
        limit: Maximum number of items to return.
        cursor: Pagination cursor.
        sort: Sort field.
        order: Sort order.
        query: Search query string.

    Returns:
        Paginated list of marketplace skills.
    """
    installed = _get_installed_skills(request)

    try:
        if source == "tencent":
            if query:
                result = await _tencent_search_skills(query, limit)
            else:
                result = await _tencent_list_skills(limit)

            skills = result.get("data", {}).get("skills", [])
            items = [_adapt_tencent_list_item(item, installed) for item in skills]
            return MarketplacePage(
                items=items,
                nextCursor=None,
                query=query,
                sort=sort,
                order=order,
            )

        elif source == "recommended":
            items = [_adapt_recommended_item(item, installed) for item in RECOMMENDED_SKILLS]
            # Filter by query if provided
            if query:
                query_str = str(query) if hasattr(query, '__str__') else query
                items = [item for item in items if query_str.lower() in (item.displayName or "").lower() or query_str.lower() in (item.summary or "").lower()]
            return MarketplacePage(
                items=items,
                nextCursor=None,
                query=str(query) if query else "",
                sort="name",
                order="asc",
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list marketplace skills: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch skills: {str(e)}")


@router.get("/detail/{slug}", response_model=MarketplaceDetail)
async def get_marketplace_skill_detail(
    request: Request,
    slug: str,
    source: str = Query("tencent", description="Marketplace source"),
):
    """Get detailed information about a marketplace skill.

    Args:
        slug: Skill slug (identifier).
        source: Marketplace source.

    Returns:
        Detailed skill information.
    """
    installed = _get_installed_skills(request)

    try:
        if source == "tencent":
            # Tencent doesn't have detail API, return from list
            result = await _tencent_list_skills(MAX_LIMIT)
            skills = result.get("data", {}).get("skills", [])
            for item in skills:
                if item.get("slug") == slug:
                    return _adapt_tencent_list_item(item, installed)
            raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")

        elif source == "recommended":
            for item in RECOMMENDED_SKILLS:
                if item.get("slug") == slug:
                    return _adapt_recommended_item(item, installed)
            raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skill detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch skill: {str(e)}")


@router.get("/search", response_model=MarketplacePage)
async def search_marketplace_skills(
    request: Request,
    q: str = Query(..., description="Search query"),
    source: str = Query("tencent", description="Marketplace source"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Search for skills in marketplace.

    Args:
        q: Search query.
        source: Marketplace source.
        limit: Maximum results.

    Returns:
        Search results.
    """
    # Delegate to list endpoint with query
    return await list_marketplace_skills(
        request=request,
        source=source,
        limit=limit,
        query=q,
    )


@router.post("/install", response_model=InstallResult)
async def install_skill(
    request: Request,
    install_req: InstallRequest,
):
    """Install a skill from marketplace.

    Args:
        install_req: Installation request with skill slug and source.

    Returns:
        Installation result.
    """
    slug = install_req.slug
    source = install_req.source

    # 推荐列表的技能默认从 tencent 安装
    if source == "recommended":
        source = "tencent"

    skills_dir = _get_skills_dir(request)
    installed = _get_installed_skills(request)

    # Check if already installed
    if slug in installed:
        meta = installed[slug]
        return InstallResult(
            success=True,
            skillName=meta.skillName,
            version=meta.version,
            message=f"Skill already installed as '{meta.skillName}'",
        )

    try:
        if source == "tencent":
            buffer = await _tencent_download(slug)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

        # Extract to skills directory
        skill_name = _extract_skill_from_zip(buffer, skills_dir)

        # Get version info
        version = "latest"
        skill_file = skills_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            # Try to extract version from frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if fm_match:
                for line in fm_match.group(1).split("\n"):
                    if line.startswith("version:"):
                        version = line.split(":", 1)[1].strip().strip('"').strip("'")
                        break

        # Save registry metadata
        meta = RegistryMeta(
            slug=slug,
            skillName=skill_name,
            source=source,
            version=version,
            installedAt=int(__import__("time").time()),
        )
        installed[slug] = meta
        _save_registry(request, installed)

        return InstallResult(
            success=True,
            skillName=skill_name,
            version=version,
            message=f"Successfully installed '{skill_name}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install skill {slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Installation failed: {str(e)}")


@router.post("/uninstall")
async def uninstall_skill(
    request: Request,
    uninstall_req: UninstallRequest,
):
    """Uninstall a skill.

    Args:
        uninstall_req: Uninstall request with skill slug or name.

    Returns:
        Uninstall result.
    """
    identifier = uninstall_req.slug
    installed = _get_installed_skills(request)
    skills_dir = _get_skills_dir(request)
    
    # 先尝试按 slug 查找
    target_slug = identifier
    target_skill_name = None
    
    if identifier in installed:
        # 直接找到 slug
        meta = installed[identifier]
        target_skill_name = meta.skillName
    else:
        # 尝试按 skillName 反向查找 slug
        for slug, meta in installed.items():
            if meta.skillName == identifier:
                target_slug = slug
                target_skill_name = meta.skillName
                break
    
    skill_path = None
    if target_skill_name:
        skill_path = skills_dir / target_skill_name
    else:
        # 处理自建技能或不在注册表中的技能
        skill_path = skills_dir / identifier
    
    # 从注册表中删除（如果存在）
    if target_slug in installed:
        del installed[target_slug]
        _save_registry(request, installed)
    else:
        # 检查技能目录是否存在
        if not skill_path.exists():
            raise HTTPException(status_code=404, detail=f"Skill not found: {identifier}")

    # Remove skill directory
    if skill_path.exists():
        shutil.rmtree(skill_path)

    return {"success": True, "message": f"Successfully uninstalled '{identifier}'"}


@router.post("/update", response_model=InstallResult)
async def update_skill(
    request: Request,
    update_req: UpdateRequest,
):
    """Update an installed skill.

    Args:
        update_req: Update request with skill slug and source.

    Returns:
        Update result.
    """
    slug = update_req.slug
    source = update_req.source
    installed = _get_installed_skills(request)

    if slug not in installed:
        raise HTTPException(status_code=404, detail=f"Skill not installed: {slug}")

    # Perform uninstall first, then install
    meta = installed[slug]
    skills_dir = _get_skills_dir(request)
    skill_path = skills_dir / meta.skillName

    # Remove old version
    if skill_path.exists():
        shutil.rmtree(skill_path)

    # Remove from registry temporarily
    del installed[slug]
    _save_registry(request, installed)

    try:
        # Install new version
        if source == "tencent":
            buffer = await _tencent_download(slug)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

        # Extract
        skill_name = _extract_skill_from_zip(buffer, skills_dir)

        # Get version
        version = "latest"
        skill_file = skills_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if fm_match:
                for line in fm_match.group(1).split("\n"):
                    if line.startswith("version:"):
                        version = line.split(":", 1)[1].strip().strip('"').strip("'")
                        break

        # Save registry
        new_meta = RegistryMeta(
            slug=slug,
            skillName=skill_name,
            source=source,
            version=version,
            installedAt=int(__import__("time").time()),
        )
        installed[slug] = new_meta
        _save_registry(request, installed)

        return InstallResult(
            success=True,
            skillName=skill_name,
            version=version,
            message=f"Successfully updated to version {version}",
        )

    except Exception as e:
        # Restore old registry on failure
        meta.installedAt = int(__import__("time").time())
        installed[slug] = meta
        _save_registry(request, installed)
        logger.error(f"Failed to update skill {slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
