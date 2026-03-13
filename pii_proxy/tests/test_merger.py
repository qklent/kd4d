from app.detection.base import PIISpan
from app.detection.merger import SpanMerger


def test_no_overlap():
    merger = SpanMerger()
    spans = [
        PIISpan(0, 10, "INN", "7707083893", 0.99, "regex"),
        PIISpan(20, 31, "PERSON", "Иванов Иван", 0.95, "ner"),
    ]
    result = merger.merge(spans)
    assert len(result) == 2


def test_overlap_prefers_regex_over_higher_confidence_ner():
    """Regex source is preferred even when NER has higher confidence."""
    merger = SpanMerger()
    spans = [
        PIISpan(0, 10, "INN", "7707083893", 0.4, "regex"),
        PIISpan(0, 10, "ORG", "7707083893", 0.95, "ner"),
    ]
    result = merger.merge(spans)
    assert len(result) == 1
    assert result[0].source == "regex"
    assert result[0].entity_type == "INN"


def test_overlap_keeps_higher_confidence_same_source():
    """When both are NER, higher confidence wins."""
    merger = SpanMerger()
    spans = [
        PIISpan(0, 10, "PERSON", "Иванов Ива", 0.7, "ner"),
        PIISpan(0, 10, "ORG", "Иванов Ива", 0.95, "ner"),
    ]
    result = merger.merge(spans)
    assert len(result) == 1
    assert result[0].entity_type == "ORG"


def test_overlap_prefers_regex():
    merger = SpanMerger()
    spans = [
        PIISpan(0, 10, "PERSON", "Иванов Ива", 0.95, "ner"),
        PIISpan(0, 10, "INN", "7707083893", 0.90, "regex"),
    ]
    result = merger.merge(spans)
    assert len(result) == 1
    assert result[0].source == "regex"


def test_empty_spans():
    merger = SpanMerger()
    assert merger.merge([]) == []
