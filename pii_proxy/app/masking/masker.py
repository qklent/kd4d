from __future__ import annotations

from collections import defaultdict

from ..detection.base import PIISpan


class PIIMasker:
    def mask(self, text: str, spans: list[PIISpan]) -> tuple[str, dict[str, str]]:
        counters: defaultdict[str, int] = defaultdict(int)
        mapping: dict[str, str] = {}

        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            counters[span.entity_type] += 1
            placeholder = f"[{span.entity_type}_{counters[span.entity_type]}]"
            mapping[placeholder] = span.text
            text = text[: span.start] + placeholder + text[span.end :]

        return text, mapping
