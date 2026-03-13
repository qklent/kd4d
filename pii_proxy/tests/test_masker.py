from app.detection.base import PIISpan
from app.masking.masker import PIIMasker


def test_mask_single_span():
    masker = PIIMasker()
    text = "Мой ИНН 7707083893"
    spans = [PIISpan(start=8, end=18, entity_type="INN", text="7707083893", confidence=0.99, source="regex")]
    masked, mapping = masker.mask(text, spans)
    assert masked == "Мой ИНН [INN_1]"
    assert mapping["[INN_1]"] == "7707083893"


def test_mask_multiple_spans():
    masker = PIIMasker()
    text = "ИНН 7707083893, имя Иванов Иван"
    spans = [
        PIISpan(start=4, end=14, entity_type="INN", text="7707083893", confidence=0.99, source="regex"),
        PIISpan(start=20, end=31, entity_type="PERSON", text="Иванов Иван", confidence=0.95, source="ner"),
    ]
    masked, mapping = masker.mask(text, spans)
    assert "[INN_1]" in masked
    assert "[PERSON_1]" in masked
    assert mapping["[INN_1]"] == "7707083893"
    assert mapping["[PERSON_1]"] == "Иванов Иван"


def test_mask_preserves_text_without_spans():
    masker = PIIMasker()
    text = "Просто текст без PII"
    masked, mapping = masker.mask(text, [])
    assert masked == text
    assert mapping == {}
