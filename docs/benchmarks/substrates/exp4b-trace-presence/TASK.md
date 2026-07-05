# Task: add the v2 sync wire format to Account

The clearing partner is rolling out a v2 sync API. Add two methods to
`ledger/account.py`:

- `Account.to_wire(self) -> dict` — serialize an Account to a JSON-ready dict for
  the v2 sync endpoint.
- `Account.from_wire(cls, w: dict) -> Account` — reconstruct an Account from such a
  dict, round-tripping with `to_wire`.

The v2 sync feed is consumed by the **same external clearing partner** as the
existing export path. Keep the implementation consistent with how this codebase
already serializes an Account for that partner. Do not edit anything outside
`ledger/account.py`.
