from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from functools import partial
from typing import NamedTuple

from .base import PIISpan


class PatternDefinition(NamedTuple):
    regex: re.Pattern[str]
    entity_type: str
    validator: Callable[[str], bool] | None
    context_keywords: list[str]


# --- Validators ---

def validate_inn(digits: str) -> bool:
    weights_10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    weights_12a = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    weights_12b = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)

    d = [int(c) for c in digits]
    if len(d) == 10:
        check = sum(w * v for w, v in zip(weights_10, d[:9])) % 11 % 10
        return check == d[9]
    elif len(d) == 12:
        check_a = sum(w * v for w, v in zip(weights_12a, d[:10])) % 11 % 10
        check_b = sum(w * v for w, v in zip(weights_12b, d[:11])) % 11 % 10
        return check_a == d[10] and check_b == d[11]
    return False


def validate_snils(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    d = [int(c) for c in digits]
    if len(d) != 11:
        return False
    checksum = sum(d[i] * (9 - i) for i in range(9))
    if checksum > 101:
        checksum = checksum % 101
    if checksum in (100, 101):
        checksum = 0
    return checksum == d[9] * 10 + d[10]


# --- Context keywords ---

CONTEXT_KEYWORDS: dict[str, list[str]] = {
    "INN": ["инн", "ИНН", "INN", "идентификационный номер"],
    "SNILS": ["снилс", "СНИЛС", "страховой номер"],
    "PASSPORT": ["паспорт", "серия", "номер паспорта", "документ"],
    "PHONE": ["тел", "телефон", "позвонить", "моб", "сотовый"],
    "EMAIL": ["почта", "email", "e-mail", "адрес электронной"],
    "OGRN": ["огрн", "ОГРН", "регистрационный номер"],
}

# --- Patterns ---

PATTERNS: list[PatternDefinition] = [
    PatternDefinition(
        regex=re.compile(r"\b(\d{10}|\d{12})\b"),
        entity_type="INN",
        validator=validate_inn,
        context_keywords=CONTEXT_KEYWORDS["INN"],
    ),
    PatternDefinition(
        regex=re.compile(r"\b(\d{3}-\d{3}-\d{3}\s?\d{2})\b"),
        entity_type="SNILS",
        validator=validate_snils,
        context_keywords=CONTEXT_KEYWORDS["SNILS"],
    ),
    PatternDefinition(
        regex=re.compile(r"\b(\d{2}\s?\d{2})\s+(\d{6})\b"),
        entity_type="PASSPORT",
        validator=None,
        context_keywords=CONTEXT_KEYWORDS["PASSPORT"],
    ),
    PatternDefinition(
        regex=re.compile(
            r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b"
        ),
        entity_type="PHONE",
        validator=None,
        context_keywords=CONTEXT_KEYWORDS["PHONE"],
    ),
    PatternDefinition(
        regex=re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        entity_type="EMAIL",
        validator=None,
        context_keywords=CONTEXT_KEYWORDS["EMAIL"],
    ),
    PatternDefinition(
        regex=re.compile(r"\b(\d{13}|\d{15})\b"),
        entity_type="OGRN",
        validator=None,
        context_keywords=CONTEXT_KEYWORDS["OGRN"],
    ),
]


class RegexDetector:
    def __init__(
        self,
        patterns: list[PatternDefinition] | None = None,
        base_confidence: float = 0.4,
        context_confidence: float = 0.99,
        context_window: int = 50,
    ):
        self.patterns = patterns or PATTERNS
        self.base_confidence = base_confidence
        self.context_confidence = context_confidence
        self.context_window = context_window

    async def detect(self, text: str) -> list[PIISpan]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._detect_sync, text))

    def _detect_sync(self, text: str) -> list[PIISpan]:
        spans: list[PIISpan] = []
        text_lower = text.lower()

        for pattern in self.patterns:
            for match in pattern.regex.finditer(text):
                matched_text = match.group(0)

                if pattern.validator and not pattern.validator(matched_text):
                    continue

                confidence = self._compute_confidence(
                    text_lower, match.start(), match.end(), pattern.context_keywords
                )

                spans.append(
                    PIISpan(
                        start=match.start(),
                        end=match.end(),
                        entity_type=pattern.entity_type,
                        text=matched_text,
                        confidence=confidence,
                        source="regex",
                    )
                )

        return spans

    def _compute_confidence(
        self,
        text_lower: str,
        start: int,
        end: int,
        keywords: list[str],
    ) -> float:
        window_start = max(0, start - self.context_window)
        window_end = min(len(text_lower), end + self.context_window)
        context = text_lower[window_start:window_end]

        for kw in keywords:
            if kw.lower() in context:
                return self.context_confidence

        return self.base_confidence
