"""BM25 index persistence."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PERSISTENCE_SECRET_ENV = "NANOBOT_PERSISTENCE_SECRET"
_SIGNATURE_FILE = "bm25_signature.txt"


def _get_signing_key() -> bytes:
    secret = os.environ.get(_PERSISTENCE_SECRET_ENV, "")
    if not secret:
        secret = hashlib.sha256(b"nanobot-bm25-default-key").hexdigest()
    return secret.encode("utf-8")


def _sign_data(data: bytes) -> str:
    return hmac.new(_get_signing_key(), data, hashlib.sha256).hexdigest()


def _verify_signature(data: bytes, signature: str) -> bool:
    expected = _sign_data(data)
    return hmac.compare_digest(expected, signature)


class BM25Persist:
    """Persistence manager for BM25 indexes.

    Since rank_bm25 doesn't provide built-in persistence,
    this class handles saving and loading BM25 indexes using pickle
    with HMAC signature verification for security.

    Attributes:
        persist_path: Directory for storing index files.
    """

    INDEX_FILE = "bm25_index.pkl"
    DOCS_FILE = "bm25_docs.pkl"
    SIGNATURE_FILE = "bm25_signature.txt"

    def __init__(self, persist_path: Path):
        self.persist_path = Path(persist_path)
        self.index_file = self.persist_path / self.INDEX_FILE
        self.docs_file = self.persist_path / self.DOCS_FILE
        self.signature_file = self.persist_path / self.SIGNATURE_FILE

    def save(
        self,
        bm25_index: Any,
        docs: list[dict[str, Any]],
        id_map: dict[int, str]
    ) -> None:
        """Save BM25 index and associated data with HMAC signature.

        Args:
            bm25_index: BM25Okapi index object.
            docs: List of document dicts.
            id_map: Mapping from index to document ID.
        """
        self.persist_path.mkdir(parents=True, exist_ok=True)

        try:
            index_data = pickle.dumps(bm25_index, protocol=pickle.HIGHEST_PROTOCOL)
            docs_data = pickle.dumps({"docs": docs, "id_map": id_map}, protocol=pickle.HIGHEST_PROTOCOL)
            
            combined_data = index_data + docs_data
            signature = _sign_data(combined_data)
            
            with open(self.index_file, "wb") as f:
                f.write(index_data)

            with open(self.docs_file, "wb") as f:
                f.write(docs_data)

            with open(self.signature_file, "w") as f:
                f.write(signature)

            logger.info(f"BM25 index saved: {len(docs)} documents")
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")
            raise

    def load(self) -> tuple[Any, list[dict[str, Any]], dict[int, str]] | None:
        """Load BM25 index and associated data with signature verification.

        Returns:
            Tuple of (bm25_index, docs, id_map) or None if not found or signature invalid.
        """
        if not self.index_file.exists() or not self.docs_file.exists():
            return None

        try:
            index_data = self.index_file.read_bytes()
            docs_data = self.docs_file.read_bytes()
            
            if self.signature_file.exists():
                stored_signature = self.signature_file.read_text().strip()
                combined_data = index_data + docs_data
                if not _verify_signature(combined_data, stored_signature):
                    logger.error("BM25 index signature verification failed! File may have been tampered with.")
                    return None
            else:
                logger.warning("BM25 index signature file not found. Loading without verification (legacy format).")

            bm25_index = pickle.loads(index_data)
            data = pickle.loads(docs_data)

            docs = data["docs"]
            id_map = data["id_map"]

            logger.info(f"BM25 index loaded: {len(docs)} documents")
            return bm25_index, docs, id_map
        except Exception as e:
            logger.warning(f"Failed to load BM25 index: {e}")
            return None

    def exists(self) -> bool:
        """Check if persisted index exists.

        Returns:
            True if both index files exist.
        """
        return self.index_file.exists() and self.docs_file.exists()

    def clear(self) -> None:
        """Delete persisted index files."""
        try:
            if self.index_file.exists():
                self.index_file.unlink()
            if self.docs_file.exists():
                self.docs_file.unlink()
            if self.signature_file.exists():
                self.signature_file.unlink()
            logger.info("BM25 index files deleted")
        except Exception as e:
            logger.warning(f"Failed to delete BM25 index files: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about persisted index.

        Returns:
            Dict with file existence and size info.
        """
        stats = {
            "exists": self.exists(),
            "index_file": str(self.index_file),
            "docs_file": str(self.docs_file)
        }

        if self.index_file.exists():
            stats["index_size"] = self.index_file.stat().st_size

        if self.docs_file.exists():
            stats["docs_size"] = self.docs_file.stat().st_size

        return stats
