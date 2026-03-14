"""Whitelist management for web authentication."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class WhitelistManager:
    """Manages browser fingerprint whitelist for authentication."""

    def __init__(self, whitelist_file: Path):
        self.whitelist_file = whitelist_file
        self._lock = threading.Lock()
        self._fingerprints: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._fingerprints = set(data.get("fingerprints", []))
                logger.info(
                    f"Loaded {len(self._fingerprints)} fingerprints from whitelist"
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load whitelist: {e}")
                self._fingerprints = set()
        else:
            self._save()

    def _save(self) -> None:
        try:
            self.whitelist_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.whitelist_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"fingerprints": list(self._fingerprints)},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except IOError as e:
            logger.error(f"Failed to save whitelist: {e}")

    @staticmethod
    def hash_fingerprint(fingerprint: str) -> str:
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def is_allowed(self, fingerprint_hash: str) -> bool:
        if not fingerprint_hash:
            return False
        with self._lock:
            return fingerprint_hash in self._fingerprints

    def add_fingerprint(self, fingerprint_hash: str) -> bool:
        if not fingerprint_hash:
            return False
        with self._lock:
            if fingerprint_hash in self._fingerprints:
                return True
            self._fingerprints.add(fingerprint_hash)
            self._save()
            logger.info(f"Added new fingerprint to whitelist")
            return True

    def remove_fingerprint(self, fingerprint_hash: str) -> bool:
        with self._lock:
            if fingerprint_hash in self._fingerprints:
                self._fingerprints.remove(fingerprint_hash)
                self._save()
                logger.info(f"Removed fingerprint from whitelist")
                return True
            return False

    def get_all_fingerprints(self) -> Set[str]:
        with self._lock:
            return self._fingerprints.copy()

    def clear(self) -> None:
        with self._lock:
            self._fingerprints.clear()
            self._save()
            logger.info("Cleared all fingerprints from whitelist")
