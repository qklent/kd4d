from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class PIISpan:
    start: int
    end: int
    entity_type: str
    text: str
    confidence: float
    source: str  # "regex" | "ner"


class BaseDetector(Protocol):
    async def detect(self, text: str) -> list[PIISpan]: ...
