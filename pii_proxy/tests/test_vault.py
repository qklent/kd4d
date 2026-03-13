import time

from app.masking.vault import SessionVault


def test_store_and_retrieve():
    vault = SessionVault(ttl_seconds=60)
    vault.store("s1", {"[INN_1]": "123"})
    assert vault.get_mapping("s1") == {"[INN_1]": "123"}


def test_merge_mappings():
    vault = SessionVault(ttl_seconds=60)
    vault.store("s1", {"[INN_1]": "123"})
    vault.store("s1", {"[PERSON_1]": "Иван"})
    mapping = vault.get_mapping("s1")
    assert mapping["[INN_1]"] == "123"
    assert mapping["[PERSON_1]"] == "Иван"


def test_expired_returns_empty():
    vault = SessionVault(ttl_seconds=0)
    vault.store("s1", {"[INN_1]": "123"})
    time.sleep(0.01)
    assert vault.get_mapping("s1") == {}


def test_missing_session_returns_empty():
    vault = SessionVault()
    assert vault.get_mapping("nonexistent") == {}


def test_cleanup_expired():
    vault = SessionVault(ttl_seconds=0)
    vault.store("s1", {"[INN_1]": "123"})
    time.sleep(0.01)
    vault.cleanup_expired()
    assert "s1" not in vault._store
