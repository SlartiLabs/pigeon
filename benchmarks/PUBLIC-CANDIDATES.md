# Public benchmark repos — verified candidates (the reproducible headline)

These three **external, third-party OSS** repos were run through
`PUBLIC-REPO-CRITERIA.md` and verified by actually cloning, installing, and
running each test suite at the pinned SHA. They are identity-neutral (no link to
the author/alias), so naming them here carries no opsec risk (see PROTOCOL §0).
They give the rubric's domain spread: one CLI tool, one library, one
service/framework. **Numbers are never pooled** — three honest per-repo results.

Verified 2026-06-18.

## Slot 1 — CLI tool: `cookiecutter`
- Repo: https://github.com/cookiecutter/cookiecutter
- License: **BSD-3-Clause** · Pinned SHA: `c88fbe921c97c58b65f1883ba90a0ab53cc91b34`
- Size: 3,186 non-test Python LOC · 17 modules
  (cli, config, environment, exceptions, extensions, find, generate, hooks,
  log, main, prompt, replay, repository, utils, vcs, zipfile, __main__)
- Suite: 379 passed / 4 skipped (Windows-only) in ~6.3 s · hermetic (network
  mocked via pytest-mock; conftest only monkeypatches HOME)
- Install: `pip install -e .` then `pip install pytest pytest-cov pytest-mock freezegun`
  (the `test` group is a PEP-735 dependency-group, not a PEP-508 extra)
- Pre-declared cross-boundary task: add a built-in Jinja2 extension/filter
  (e.g. `slugify_custom`) registered in `extensions.py`, surfaced through the
  extension-loading logic in `environment.py`, exercised end-to-end in
  `generate.py`. **Acceptance:** `pytest tests/test_extensions.py
  tests/test_generate_files.py -q` green, plus a new test asserting a template
  using `{{ cookiecutter.name | slugify_custom }}` renders the slugified output.
- Run notes: some tests write to `/tmp` subdirs — isolate per-run tmpdirs to
  avoid collision; `vcs.py` shells out to git/hg (git is in PATH).

## Slot 2 — Library: `marshmallow`
- Repo: https://github.com/marshmallow-code/marshmallow
- License: **MIT** · Pinned SHA: `7b4ab6a08292a3abacb88aaaf5c7a97c7bd5ebf4`
- Size: 4,830 non-test Python LOC · 12 modules
  (schema, fields, validate, decorators, utils, exceptions, error_store,
  class_registry, orderedset, types, constants, experimental/context)
- Suite: 1178 passed / 0 skipped in ~2.8 s · hermetic (no network/secrets;
  the only "http" hits are URL strings in comments)
- Install: `pip install -e .` then `pip install pytest simplejson`
  (`[tests]` is a dependency-group, not an extra)
- Pre-declared cross-boundary task: raise a `SchemaError` at Schema
  class-creation time when two fields declare the same `data_key` — spans the
  Schema metaclass/binding in `schema.py` and the `Field.data_key` attribute in
  `fields.py`. **Acceptance:** a new `tests/test_schema.py` test asserting that
  defining `a = fields.Str(data_key="x"); b = fields.Int(data_key="x")` raises,
  then `pytest tests/test_schema.py -q` exits 0.
- Run notes: very small package — keep tasks genuinely cross-boundary or both
  arms tie; ~2.8 s suite means wall-clock metrics are noisy (lean on tokens +
  interventions).

## Slot 3 — Service / framework: `flask`
- Repo: https://github.com/pallets/flask
- License: **BSD-3-Clause** · Pinned SHA: `36e4a824f340fdee7ed50937ba8e7f6bc7d17f81`
- Size: ~6,961 non-test Python LOC · 20 modules
  (app, blueprints, cli, config, ctx, debughelpers, globals, helpers, logging,
  sessions, signals, templating, testing, typing, views, wrappers, __main__,
  json/, sansio/)
- Suite: 491 passed / 0 skipped in ~2.4 s · hermetic (HTTP mocked via
  Werkzeug's test client; no network/secrets/cloud/GPU)
- Install: `pip install -e ".[async]" "pytest<9" asgiref python-dotenv`
  (pytest 9.x breaks collection via removed `_pytest.monkeypatch.notset`; asgiref
  needed or async tests silently skip)
- Pre-declared cross-boundary task: add a `STRICT_SLASHES` default config key so
  `app.config["STRICT_SLASHES"] = False` propagates to all URL rules without
  per-route flags — spans `sansio/app.py` (config schema + `add_url_rule`),
  `app.py` (WSGI layer), and `config.py` (defaults). **Acceptance:**
  `pytest tests/test_basic.py -k test_url_mapping` green, plus a new test
  asserting the config makes `/about` and `/about/` both return 200.
- Run notes: dev snapshot (`3.2.0.dev`) — HEAD drifts, so pin to this SHA; thin
  glue framework, tasks tend to touch 2–3 files (fine for focused
  cross-boundary work, not deep refactors).

---

### Backup
`starlette` (encode/starlette, BSD-3) was queued as an alternate for the
service/app slot; flask passed cleanly so it is held in reserve, not used.

### Status
Per-candidate verification checklist (PUBLIC-REPO-CRITERIA.md) satisfied for all
three. Next: build the WITH/WITHOUT harness and **pilot one task end-to-end**
(decision: start with 1, scale to 3 or 5 if the harness holds).
