from datetime import datetime, timezone

from ledger.account import Account


def test_construct():
    dt = datetime.fromtimestamp(1700000000, tz=timezone.utc)
    a = Account(name="alice", balance_cents=500, created=dt, note="hi")
    assert a.name == "alice"
    assert a.balance_cents == 500
    assert a.note == "hi"


def test_equality():
    dt = datetime.fromtimestamp(1700000000, tz=timezone.utc)
    assert Account("a", 1, dt) == Account("a", 1, dt)


def test_default_note_none():
    dt = datetime.fromtimestamp(1700000000, tz=timezone.utc)
    assert Account("a", 1, dt).note is None
