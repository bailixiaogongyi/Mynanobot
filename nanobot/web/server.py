"""FastAPI server entry point for nanobot Web UI."""

from __future__ import annotations

import json
import logging
import secrets
import string
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from nanobot.agent.loop import AgentLoop
    from nanobot.config.schema import Config
    from nanobot.session.manager import SessionManager

logger = logging.getLogger(__name__)

LOGIN_PAGE_PATH = Path(__file__).parent / "static" / "login.html"
PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/verify",
    "/api/auth/status",
    "/api/health",
}
STATIC_EXTENSIONS = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"}


def generate_secure_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    password = []
    password.append(secrets.choice(string.ascii_uppercase))
    password.append(secrets.choice(string.ascii_lowercase))
    password.append(secrets.choice(string.digits))
    password.append(secrets.choice("!@#$%^&*"))
    for _ in range(length - 4):
        password.append(secrets.choice(alphabet))
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def _save_config_with_password(config: Config, password: str) -> None:
    try:
        from nanobot.config.loader import get_config_path

        config_path = get_config_path()
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        if "gateway" not in data:
            data["gateway"] = {}
        if "web_ui" not in data["gateway"]:
            data["gateway"]["web_ui"] = {}
        if "auth" not in data["gateway"]["web_ui"]:
            data["gateway"]["web_ui"]["auth"] = {}
        data["gateway"]["web_ui"]["auth"]["password"] = password

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated password saved to config file: {config_path}")
    except Exception as e:
        logger.error(f"Failed to save generated password to config: {e}")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_enabled = getattr(request.app.state, "auth_enabled", False)

        if not auth_enabled:
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if request.url.path == "/login.html":
            return await call_next(request)

        for ext in STATIC_EXTENSIONS:
            if request.url.path.endswith(ext):
                return await call_next(request)

        whitelist_manager = request.app.state.whitelist_manager

        fp_header = request.headers.get("X-Device-Fingerprint", "")
        if fp_header and whitelist_manager.is_allowed(fp_header):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if whitelist_manager.is_allowed(token):
                return await call_next(request)

        fingerprint = request.cookies.get("nanobot_fp")
        if fingerprint and whitelist_manager.is_allowed(fingerprint):
            return await call_next(request)

        if request.url.path == "/" or request.url.path == "/index.html":
            if LOGIN_PAGE_PATH.exists():
                with open(LOGIN_PAGE_PATH, "r", encoding="utf-8") as f:
                    return Response(content=f.read(), media_type="text/html")

        return Response(content='{"detail":"Unauthorized"}', status_code=401, media_type="application/json")


def create_app(
    config: Config,
    agent: AgentLoop,
    session_manager: SessionManager,
) -> FastAPI:
    """Create FastAPI application.

    Args:
        config: nanobot configuration.
        agent: Agent loop instance.
        session_manager: Session manager instance.

    Returns:
        FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Web UI starting up")

        auth_config = getattr(config.gateway.web_ui, "auth", None)
        if auth_config and auth_config.enabled:
            from nanobot.web.whitelist import WhitelistManager

            whitelist_file = Path(auth_config.whitelist_file).expanduser()
            app.state.whitelist_manager = WhitelistManager(whitelist_file)

            auth_password = auth_config.password or ""
            if not auth_password:
                auth_password = generate_secure_password()
                auth_config.password = auth_password
                _save_config_with_password(config, auth_password)
                logger.warning("=" * 60)
                logger.warning("WEB UI AUTHENTICATION PASSWORD GENERATED")
                logger.warning("Please save this password securely!")
                logger.warning("It will NOT be shown again.")
                logger.warning("=" * 60)

            app.state.auth_password = auth_password
            app.state.auth_enabled = True
            logger.info(f"Web authentication enabled, whitelist file: {whitelist_file}")
        else:
            app.state.auth_enabled = False
            app.state.whitelist_manager = None
            app.state.auth_password = ""

        yield

        logger.info("Web UI shutting down")

    app = FastAPI(
        title="AiMate Web UI",
        version="1.0.0",
        description="Web interface for AiMate AI assistant",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(AuthMiddleware)

    app.state.config = config
    app.state.agent = agent
    app.state.session_manager = session_manager

    if hasattr(agent, 'role_manager'):
        app.state.role_manager = agent.role_manager

    if hasattr(agent, 'task_manager'):
        app.state.task_manager = agent.task_manager

    if hasattr(agent, 'subagent_manager'):
        app.state.subagent_manager = agent.subagent_manager
    else:
        app.state.subagent_manager = None

    if hasattr(agent, 'memory'):
        app.state.memory_store = agent.memory

    if hasattr(agent, 'bus'):
        app.state.bus = agent.bus

    from nanobot.web.routes import auth, chat, config as config_routes, marketplace, notes, skills
    from nanobot.web.routes.upload import router as upload_router
    from nanobot.web.routes.agents import router as agents_router
    from nanobot.web.routes.dashboard import router as dashboard_router
    from nanobot.web.routes.stats import router as stats_router

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
    app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
    app.include_router(marketplace.router, prefix="/api/marketplace", tags=["marketplace"])
    app.include_router(config_routes.router, prefix="/api/config", tags=["config"])
    app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
    app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
    app.include_router(stats_router, prefix="/api", tags=["stats"])

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok"}

    @app.get("/login.html")
    async def login_page():
        if LOGIN_PAGE_PATH.exists():
            with open(LOGIN_PAGE_PATH, "r", encoding="utf-8") as f:
                return Response(content=f.read(), media_type="text/html")
        return Response(content="Login page not found", status_code=404)

    static_dir = Path(__file__).parent / "dist"
    if static_dir.exists() and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists() and (static_dir / "index.html").exists():
            app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


def run_server(
    config: Config,
    agent: AgentLoop,
    session_manager: SessionManager,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Run the FastAPI server.

    Args:
        config: nanobot configuration.
        agent: Agent loop instance.
        session_manager: Session manager instance.
        host: Host to bind to (defaults to config.gateway.web_ui.host).
        port: Port to bind to (defaults to config.gateway.web_ui.port).
    """
    import uvicorn

    host = host or config.gateway.web_ui.host
    port = port or config.gateway.web_ui.port

    app = create_app(config, agent, session_manager)

    logger.info(f"Starting Web UI on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
