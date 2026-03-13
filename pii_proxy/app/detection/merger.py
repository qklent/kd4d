from __future__ import annotations

from .base import PIISpan


class SpanMerger:
    def merge(self, spans: list[PIISpan]) -> list[PIISpan]:
        if not spans:
            return []

        spans.sort(key=lambda s: (s.start, -s.confidence))

        merged = [spans[0]]
        for span in spans[1:]:
            prev = merged[-1]
            if span.start < prev.end:
                if span.confidence > prev.confidence or (
                    span.source == "regex" and prev.source != "regex"
                ):
                    merged[-1] = span
            else:
                merged.append(span)

        return merged
