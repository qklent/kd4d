import pytest

from app.detection.merger import SpanMerger
from app.detection.pipeline import DetectionPipeline
from app.detection.regex_detector import RegexDetector


@pytest.mark.asyncio
async def test_pipeline_with_regex_only():
    pipeline = DetectionPipeline(
        detectors=[RegexDetector()],
        merger=SpanMerger(),
    )
    spans = await pipeline.detect("ИНН 7707083893, email: test@example.com")
    types = {s.entity_type for s in spans}
    assert "INN" in types
    assert "EMAIL" in types
