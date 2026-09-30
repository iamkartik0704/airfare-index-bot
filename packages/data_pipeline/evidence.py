"""Content-addressed store for raw response bodies (decision D2, doc 02 §4).

Bodies are gzip-compressed and stored under their SHA-256, so identical
responses are stored once and a stored body can be verified against its
hash at any time. ``storage_uri`` is logical (``evidence://ab/cd/<sha>.gz``)
and resolved against the configured directory, so the store can move (or be
swapped for S3 in production, doc 16 B) without rewriting the database.
"""

from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path

from packages.domain.exceptions import NotFoundError, PersistenceError

SCHEME = "evidence://"


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _path(self, sha256: str) -> Path:
        return self._root / sha256[:2] / sha256[2:4] / f"{sha256}.gz"

    def put(self, body: bytes) -> tuple[str, str]:
        """Store ``body``; returns ``(sha256, storage_uri)``. Idempotent."""
        sha = hashlib.sha256(body).hexdigest()
        path = self._path(sha)
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
                tmp.write_bytes(gzip.compress(body, compresslevel=6, mtime=0))
                tmp.replace(path)  # atomic: readers never see a partial file
            except OSError as exc:
                raise PersistenceError("could not write evidence", sha256=sha) from exc
        return sha, f"{SCHEME}{sha[:2]}/{sha[2:4]}/{sha}.gz"

    def get(self, storage_uri: str) -> bytes:
        if not storage_uri.startswith(SCHEME):
            raise PersistenceError("unsupported evidence URI", uri=storage_uri)
        sha = storage_uri.rsplit("/", 1)[-1].removesuffix(".gz")
        path = self._path(sha)
        try:
            body = gzip.decompress(path.read_bytes())
        except FileNotFoundError as exc:
            raise NotFoundError("evidence body missing", uri=storage_uri) from exc
        if hashlib.sha256(body).hexdigest() != sha:
            raise PersistenceError("evidence body failed its integrity check", uri=storage_uri)
        return body
