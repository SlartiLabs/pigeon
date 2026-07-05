from datetime import datetime, timezone

from ledger.account import Account
from ledger.sync_codec import decode_from_partner, encode_for_partner


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


def test_partner_codec_roundtrip():
    # Exercises only the existing partner codec; the v2 Account.to_wire convention
    # under test is NOT encoded here (the cue lives in ledger/sync_codec.py).
    dt = datetime.fromtimestamp(1700000000, tz=timezone.utc)
    w = encode_for_partner("alice", 500, dt, note="hi")
    back = decode_from_partner(w)
    assert back["name"] == "alice" and back["balance_cents"] == 500
