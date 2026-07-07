# Stage 2 Cross-Model Benchmark, raw transcript archive

> [!CAUTION]
> **Data-integrity notice, read before citing any number below.** This folder is a
> raw-transcript ARCHIVE, and three of its four arms are contaminated. The
> `sonnet + agy` arms reporting **0/12** and **0/8** (Exp-5 Recoverability, Necessity
> With-Derived, Necessity Pointers-Only) are **NOT results**: at run time
> `telemetry_flags.agy` had been set to `[--json]`, but the `agy` CLI has no `--json`
> flag, so under `--telemetry` it printed its usage and **exited without editing**,
> recording a false `0/N`. This is verifiable in this very archive: see the flag-break
> and `# exit 2` in the receiver transcripts, e.g.
> `nec-with-derived/t1/.pigeon/coordinate/logs/*to_wire.log`. Only the **all-agy 7/8**
> arm (`nec-wd-allagy`) ran clean.
>
> **The authoritative, corrected Stage 2 results are elsewhere**, from a clean re-run
> with `telemetry_flags.agy: []`: see [`../report.md`](../report.md) section 9.1 and
> [`../results/stage2-cross-model-report.md`](../results/stage2-cross-model-report.md),
> with committed per-arm ledgers under [`../results/stage2/`](../results/stage2/). The
> corrected verdict: the necessity law replicates on Gemini (controlled all-agy
> pointers-only 0/8 vs with-derived 7/8, Fisher p approx 0.0014); the `sonnet -> agy`
> with-derived arms were separately agy-no-op confounded (a GATE-C execution gap).
> This archive is retained as evidence of the flag-break, not as findings.

## Executive Summary & Key Results (contaminated, see the notice above)

This report consolidates all trial results, mechanism checks, canonical token counts (`o200k_base` encoding), and estimated cost breakdowns across all four Stage 2 cross-model benchmark evaluations.

> [!IMPORTANT]
> **Key Finding, All-Gemini Necessity Hypothesis Validated (`7/8` Pass Rate):**
> When Gemini (`agy`) serves as both architect and receiver in the necessity chain (`with-derived-agy agy agy`), it achieved a **7/8 (87.5%) pass rate**. In contrast, the pointers-only arm (`pointers-only-agy`) achieved **0/8 (0%) pass rate**. This confirms that carried reasoning residue (`state.derived`) is strictly necessary for cross-agent task handoff when using Gemini.

---

## 📊 Summary Comparison Across All Arms

Est. cost is the **canonical-recount estimate** (`o200k_base` tokens x the verified
2026-07-07 rate snapshot: agy/Gemini-3.5-Flash $1.50/$9.00, sonnet $3/$15 per Mtok),
regenerated from the prior placeholder rates (agy was $0.30/$2.50, ~4x low). It is
NOT a bill: the transcript is argv+stdout only, so it undercounts the input the
agents read via tools; the per-trial `cost_usd` in the sections below is the
*measured* sonnet-architect spend and is much larger. Token counts are unchanged
(same tokenizer).

| Benchmark Run | Arm / Model Split | N | Pass Rate (`accept_rc==0`) | Total Canonical Tokens | Est. Cost (USD, recount) | Persisted Artifact Path |
|---|---|---|---|---|---|---|
| **All-Gemini Necessity** | `with-derived-agy` (`agy` + `agy`) | 8 | **7 / 8 (87.5%)** | 11,553 tok | $0.0801 | [`./nec-wd-allagy`](./nec-wd-allagy) |
| **Necessity (With-Derived)** | `with-derived-agy` (`sonnet` + `agy`) | 8 | **0 / 8 (0.0%)** | 9,391 tok | $0.0900 | [`./nec-with-derived`](./nec-with-derived) |
| **Necessity (Pointers-Only)** | `pointers-only-agy` (`sonnet` + `agy`) | 8 | **0 / 8 (0.0%)** | 8,077 tok | $0.0785 | [`./nec-pointers-only`](./nec-pointers-only) |
| **Exp-5 Recoverability** | `with-derived-agy` (`sonnet` + `agy`) | 12 | **0 / 12 (0.0%)** | 15,924 tok | $0.1582 | [`./exp5-with-derived`](./exp5-with-derived) |

---

## 1. All-Gemini Necessity Arm (`nec-wd-allagy`, N=8)

- **Config Split:** `architect=agy`, `to_wire=agy`, `from_wire=agy`
- **Result:** **7 / 8 Pass (87.5%)**
- **Persisted Location:** [`./nec-wd-allagy`](./nec-wd-allagy)

### Detailed Trial Log

| Trial | `accept_rc` | Result | Wall (s) | `recv_fired` | `injected` | `used_contract` |
|---|---|---|---|---|---|---|
| **1** | **0** | **PASS** | 121s | 1 | 1 | 2 |
| **2** | **0** | **PASS** | 183s | 1 | 1 | 2 |
| **3** | **0** | **PASS** | 169s | 1 | 1 | 2 |
| **4** | **0** | **PASS** | 147s | 1 | 1 | 2 |
| **5** | **0** | **PASS** | 122s | 1 | 1 | 2 |
| **6** | 1 | FAIL | 157s | 1 | 1 | 1 |
| **7** | **0** | **PASS** | 198s | 1 | 1 | 2 |
| **8** | **0** | **PASS** | 138s | 1 | 1 | 2 |

---

## 2. Necessity Side, With-Derived (`nec-with-derived`, N=8)

- **Config Split:** `architect=sonnet`, `to_wire=agy`, `from_wire=agy`
- **Result:** **0 / 8 Pass (0.0%)**
- **Persisted Location:** [`./nec-with-derived`](./nec-with-derived)

### Detailed Trial Log

| Trial | `accept_rc` | Result | Cost (USD) | Wall (s) | `recv_fired` | `injected` | `used_contract` |
|---|---|---|---|---|---|---|---|
| **1** | 1 | FAIL | $0.2450 | 21s | 1 | 1 | 0 |
| **2** | 1 | FAIL | $0.2703 | 32s | 1 | 1 | 0 |
| **3** | 1 | FAIL | $0.2366 | 27s | 1 | 1 | 0 |
| **4** | 1 | FAIL | $0.1019 | 32s | 1 | 1 | 0 |
| **5** | 1 | FAIL | $0.1018 | 28s | 1 | 1 | 0 |
| **6** | 1 | FAIL | $0.1023 | 27s | 1 | 1 | 0 |
| **7** | 1 | FAIL | $0.1190 | 26s | 1 | 1 | 0 |
| **8** | 1 | FAIL | $0.0899 | 26s | 1 | 1 | 0 |

---

## 3. Necessity Side, Pointers-Only (`nec-pointers-only`, N=8)

- **Config Split:** `architect=sonnet`, `to_wire=agy`, `from_wire=agy`
- **Result:** **0 / 8 Pass (0.0%)**
- **Persisted Location:** [`./nec-pointers-only`](./nec-pointers-only)

### Detailed Trial Log

| Trial | `accept_rc` | Result | Cost (USD) | Wall (s) | `recv_fired` | `injected` | `used_contract` |
|---|---|---|---|---|---|---|---|
| **1** | 1 | FAIL | $0.3243 | 37s | 1 | 0 | 0 |
| **2** | 1 | FAIL | $0.3280 | 35s | 1 | 0 | 0 |
| **3** | 1 | FAIL | $0.1150 | 44s | 1 | 0 | 0 |
| **4** | 1 | FAIL | $0.0892 | 26s | 1 | 0 | 0 |
| **5** | 1 | FAIL | $0.1106 | 32s | 1 | 0 | 0 |
| **6** | 1 | FAIL | $0.2710 | 39s | 1 | 0 | 0 |
| **7** | 1 | FAIL | $0.1103 | 29s | 1 | 0 | 0 |
| **8** | 1 | FAIL | $0.1620 | 42s | 1 | 0 | 0 |

---

## 4. Exp-5 Recoverability Side (`exp5-with-derived`, N=12)

- **Config Split:** `architect=sonnet`, `to_wire=agy`, `from_wire=agy`
- **Result:** **0 / 12 Pass (0.0%)**
- **Persisted Location:** [`./exp5-with-derived`](./exp5-with-derived)

### Detailed Trial Log

| Trial | `accept_rc` | Result | Cost (USD) | Wall (s) | `agy_fired` | `injected` | `read_cue` |
|---|---|---|---|---|---|---|---|
| **1** | 1 | FAIL | $0.3489 | 53s | 1 | 1 | 1 |
| **2** | 1 | FAIL | $0.3499 | 53s | 1 | 1 | 1 |
| **3** | 1 | FAIL | $0.1901 | 48s | 1 | 1 | 1 |
| **4** | 1 | FAIL | $0.1616 | 56s | 1 | 1 | 1 |
| **5** | 1 | FAIL | $0.1908 | 45s | 1 | 1 | 1 |
| **6** | 1 | FAIL | $0.2043 | 63s | 1 | 1 | 1 |
| **7** | 1 | FAIL | $0.1820 | 57s | 1 | 1 | 1 |
| **8** | 1 | FAIL | $0.1970 | 58s | 1 | 1 | 1 |
| **9** | 1 | FAIL | $0.1326 | 41s | 1 | 1 | 1 |
| **10** | 1 | FAIL | $0.2574 | 82s | 1 | 1 | 1 |
| **11** | 1 | FAIL | $0.1535 | 48s | 1 | 1 | 1 |
| **12** | 1 | FAIL | $0.1380 | 40s | 1 | 1 | 1 |

---

## 🛠 Fixes Applied During Benchmark Session

1. **`agy` Telemetry & Retokenization Fix:**
   - Updated `_price_row` in [`canonical-retokenize.py`](../instruments/canonical-retokenize.py#L124) to fall back to task `runner` when `model` is empty.
   - Added an `"agy"` rate to [`prices.template.json`](../instruments/prices.template.json) (placeholder $0.30/$2.50 at the time; later verified and corrected to $1.50/$9.00 on 2026-07-07, which the Est. Cost column above reflects).
   - Embedded automatic canonical retokenization into benchmark scripts ([`run-stage2-forkA-agy.sh`](../substrates/forkA-necessity/run-stage2-forkA-agy.sh#L103) & [`run-stage2-agy-pilot.sh`](../substrates/exp5-natural/run-stage2-agy-pilot.sh#L131)).

2. **Config Flag Compatibility:**
   - Reverted `agy: [--json]` back to `agy: []` in [`.pigeon/config.yaml`](../../../.pigeon/config.yaml#L154) because `agy` CLI uses standard flags and fails if passed `-json`.
