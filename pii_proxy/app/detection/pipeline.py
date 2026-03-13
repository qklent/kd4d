from __future__ import annotations

import asyncio

from .base import BaseDetector, PIISpan
from .merger import SpanMerger


class DetectionPipeline:
    def __init__(self, detectors: list[BaseDetector], merger: SpanMerger):
        self.detectors = detectors
        self.merger = merger

    async def detect(self, text: str) -> list[PIISpan]:
        all_spans = await asyncio.gather(*[d.detect(text) for d in self.detectors])
        flat = [span for group in all_spans for span in group]
        return self.merger.merge(flat)
