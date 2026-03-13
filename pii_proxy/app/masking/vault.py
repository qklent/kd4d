from __future__ import annotations

import time


class SessionVault:
    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, tuple[dict[str, str], float]] = {}
        self.ttl = ttl_seconds

    def store(self, session_id: str, mapping: dict[str, str]) -> None:
        existing, _ = self._store.get(session_id, ({}, 0.0))
        existing.update(mapping)
        self._store[session_id] = (existing, time.time())

    def get_mapping(self, session_id: str) -> dict[str, str]:
        entry = self._store.get(session_id)
        if not entry or (time.time() - entry[1]) > self.ttl:
            return {}
        return entry[0]

    def cleanup_expired(self) -> None:
        now = time.time()
        self._store = {
            k: v for k, v in self._store.items() if (now - v[1]) <= self.ttl
        }
