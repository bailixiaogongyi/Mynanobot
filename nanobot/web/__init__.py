"""Web UI module for nanobot.

This module provides a FastAPI-based web interface for:
- Chat management (multi-session support)
- Note management (file tree, editor, semantic search)
- Skills viewing (read-only)
- Configuration management (with sensitive data masking)
"""

from nanobot.web.server import create_app, run_server

__all__ = ["create_app", "run_server"]
