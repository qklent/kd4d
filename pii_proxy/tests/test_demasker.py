from app.llm.demasker import StreamingDemasker, demask_text


def test_demask_text_simple():
    mapping = {"[INN_1]": "7707083893", "[PERSON_1]": "Иванов Иван"}
    text = "Клиент [PERSON_1], ваш ИНН [INN_1]"
    result = demask_text(text, mapping)
    assert result == "Клиент Иванов Иван, ваш ИНН 7707083893"


def test_streaming_demasker_complete_placeholder():
    mapping = {"[PERSON_1]": "Иванов Иван"}
    d = StreamingDemasker(mapping)
    result = d.feed("Клиент [PERSON_1] здесь")
    assert result == "Клиент Иванов Иван здесь"


def test_streaming_demasker_split_placeholder():
    mapping = {"[PERSON_1]": "Иванов Иван"}
    d = StreamingDemasker(mapping)

    r1 = d.feed("Клиент [PER")
    assert r1 == "Клиент "

    r2 = d.feed("SON_1] здесь")
    assert r2 == "Иванов Иван здесь"


def test_streaming_demasker_finalize():
    mapping = {"[INN_1]": "7707083893"}
    d = StreamingDemasker(mapping)

    r1 = d.feed("текст [IN")
    assert r1 == "текст "

    r2 = d.finalize()
    assert r2 == "[IN"


def test_streaming_demasker_no_placeholder():
    mapping = {"[INN_1]": "7707083893"}
    d = StreamingDemasker(mapping)
    result = d.feed("просто текст без замен")
    assert result == "просто текст без замен"


def test_streaming_demasker_buffer_overflow():
    mapping = {"[INN_1]": "7707083893"}
    d = StreamingDemasker(mapping)
    # Feed a fake partial that exceeds MAX_BUFFER
    long_text = "[" + "A" * 60
    result = d.feed(long_text)
    assert result == long_text
