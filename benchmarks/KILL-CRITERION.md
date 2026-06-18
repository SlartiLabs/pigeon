# Kill / continue criterion — LOCK COLD, before the first run

A kill-criterion chosen after seeing results is a rationalization, not a
criterion. Fill the blanks now, before any benchmark or launch. This file carries
no opsec risk and is committed deliberately.

```
LAUNCH HYPOTHESIS: developers running >=2 agent CLIs against one repo will adopt
                   a token-accounted coordination contract.

WINDOW:            ______ weeks post-launch          (strawman: 6)

KILL IF ALL OF:
  - external installs (PyPI minus own CI) < ______   (strawman: 25)
  - issues filed by strangers            = ______   (strawman: 0)
  - external contributors                = ______   (strawman: 0)

THEN: the binding constraint is TAM, not polish -> stop hardening, reconsider the
      thesis (or accept pigeon as an excellent tool for an audience of one — a
      complete and worthy outcome).
```

Weighting note (mine, to provoke yours): the **install count is the noisiest
signal** (mirrors, bots, CI). The unfakeable ones are **a stranger filing an
issue** and **an external contributor** — weight those highest; an install number
can be high and mean nothing.

A null result is *information*, not failure — but only if this block is locked
before you're emotionally invested in the outcome.
