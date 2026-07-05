# Wire-format contract for ledger's Account  (given ONLY to hop 1, by prompt)

This is the agreed JSON wire format between our serializer and a strict external
consumer. It is deliberately NOT documented anywhere in the code, and the
idiomatic Python defaults are the OPPOSITE of it. It must be carried forward to
whoever implements the producer and the consumer.

## Producer — `Account.to_wire(self) -> dict`
- keys are EXACTLY: `acct`, `cents`, `ts`  (NOT the Python field names)
  - `acct`  <- `self.name`
  - `cents` <- `self.balance_cents`
  - `ts`    <- `self.created` as Unix epoch SECONDS, as an `int`, in UTC
              (i.e. `int(self.created.timestamp())`)
- `note`: include the key ONLY if `self.note is not None`; OMIT it entirely when
  `None` (do NOT emit `null`).

## Consumer — `Account.from_wire(cls, w: dict) -> Account`  (MUST BE LENIENT)
- `acct` -> `name`
- `cents` -> `balance_cents`, accepting either an `int` OR a numeric `str`
- `ts`   -> `created` via `datetime.fromtimestamp(float(w["ts"]), tz=timezone.utc)`,
            accepting `ts` as `int` OR `float`
- a MISSING `note` key means `note = None`
- must round-trip: `from_wire(to_wire(a)) == a`
