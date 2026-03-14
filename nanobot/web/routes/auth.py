"""Authentication routes for web UI."""

from __future__ import annotations

import logging
import secrets
import time
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from nanobot.web.whitelist import WhitelistManager

logger = logging.getLogger(__name__)
router = APIRouter()

_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300


def _check_rate_limit(fingerprint: str) -> bool:
    now = time.time()
    attempts = _LOGIN_ATTEMPTS[fingerprint]
    _LOGIN_ATTEMPTS[fingerprint] = [t for t in attempts if now - t < _LOCKOUT_SECONDS]
    return len(_LOGIN_ATTEMPTS[fingerprint]) < _MAX_ATTEMPTS


def _record_failed_attempt(fingerprint: str) -> None:
    _LOGIN_ATTEMPTS[fingerprint].append(time.time())


class AuthRequest(BaseModel):
    password: str
    fingerprint: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    requires_auth: bool


class VerifyResponse(BaseModel):
    valid: bool


def get_whitelist_manager(request: Request) -> WhitelistManager:
    return request.app.state.whitelist_manager


def get_auth_password(request: Request) -> str:
    return request.app.state.auth_password


def is_auth_enabled(request: Request) -> bool:
    return getattr(request.app.state, "auth_enabled", False)


@router.post("/login")
async def login(request: Request, auth_request: AuthRequest):
    if not is_auth_enabled(request):
        return {"success": True, "message": "Authentication disabled"}

    whitelist_manager = get_whitelist_manager(request)
    auth_password = get_auth_password(request)

    if whitelist_manager.is_allowed(auth_request.fingerprint):
        return {"success": True, "message": "Already authenticated"}

    if not _check_rate_limit(auth_request.fingerprint):
        logger.warning("Rate limit exceeded for login attempts")
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please try again later.")

    if not secrets.compare_digest(auth_request.password, auth_password):
        _record_failed_attempt(auth_request.fingerprint)
        logger.warning("Failed authentication attempt")
        raise HTTPException(status_code=401, detail="Invalid password")

    whitelist_manager.add_fingerprint(auth_request.fingerprint)
    logger.info("New device authenticated and added to whitelist")
    return {"success": True, "message": "Authentication successful"}


@router.post("/verify")
async def verify_fingerprint(request: Request, auth_request: AuthRequest):
    if not is_auth_enabled(request):
        return VerifyResponse(valid=True)

    whitelist_manager = get_whitelist_manager(request)
    is_valid = whitelist_manager.is_allowed(auth_request.fingerprint)
    return VerifyResponse(valid=is_valid)


@router.get("/status")
async def get_auth_status(request: Request):
    enabled = is_auth_enabled(request)
    return AuthStatusResponse(authenticated=False, requires_auth=enabled)


@router.get("/whitelist")
async def get_whitelist(request: Request):
    if not is_auth_enabled(request):
        return {"fingerprints": [], "count": 0}

    whitelist_manager = get_whitelist_manager(request)
    fingerprints = whitelist_manager.get_all_fingerprints()
    return {
        "fingerprints": list(fingerprints),
        "count": len(fingerprints),
    }
