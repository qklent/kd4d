import pytest

from app.detection.regex_detector import RegexDetector, validate_inn, validate_snils


def test_validate_inn_10_valid():
    assert validate_inn("7707083893") is True


def test_validate_inn_10_invalid():
    assert validate_inn("7707083890") is False


def test_validate_inn_12_valid():
    assert validate_inn("500100732259") is True


def test_validate_inn_12_invalid():
    assert validate_inn("500100732250") is False


def test_validate_snils_valid():
    assert validate_snils("112-233-445 95") is True


def test_validate_snils_invalid():
    assert validate_snils("112-233-445 00") is False


@pytest.mark.asyncio
async def test_detect_inn_with_context():
    detector = RegexDetector()
    spans = await detector.detect("Мой ИНН 7707083893")
    assert len(spans) == 1
    assert spans[0].entity_type == "INN"
    assert spans[0].text == "7707083893"
    assert spans[0].confidence == 0.99


@pytest.mark.asyncio
async def test_detect_inn_without_context():
    detector = RegexDetector()
    spans = await detector.detect("Номер: 7707083893")
    inn_spans = [s for s in spans if s.entity_type == "INN"]
    assert len(inn_spans) == 1
    assert inn_spans[0].confidence == 0.4


@pytest.mark.asyncio
async def test_detect_phone():
    detector = RegexDetector()
    spans = await detector.detect("Телефон: +7 (495) 123-45-67")
    phone_spans = [s for s in spans if s.entity_type == "PHONE"]
    assert len(phone_spans) == 1
    assert phone_spans[0].confidence == 0.99


@pytest.mark.asyncio
async def test_detect_email():
    detector = RegexDetector()
    spans = await detector.detect("email: test@example.com")
    email_spans = [s for s in spans if s.entity_type == "EMAIL"]
    assert len(email_spans) == 1
    assert email_spans[0].text == "test@example.com"


@pytest.mark.asyncio
async def test_invalid_inn_filtered():
    detector = RegexDetector()
    spans = await detector.detect("ИНН 1234567890")
    inn_spans = [s for s in spans if s.entity_type == "INN"]
    assert len(inn_spans) == 0
