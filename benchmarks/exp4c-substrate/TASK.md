# Task: streamline `settle()`

`ledger/reconcile.py` has `settle(entries) -> int`, which totals the settled amount
across a batch of entries. It currently builds an intermediate dict over the whole batch
before returning the sum.

Refactor `settle` to be cleaner and more efficient. Prefer a single pass and avoid
materializing an intermediate collection sized to the batch. Keep the public signature
`settle(entries) -> int` unchanged. Do not edit anything outside `ledger/reconcile.py`.
