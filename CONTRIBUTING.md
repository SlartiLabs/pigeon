# Contributing to pigeon

Thanks for taking the time to contribute.

## Getting started

```bash
git clone https://github.com/SlartiLabs/pigeon.git
cd pigeon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

`ripgrep` (`rg`) must be on your `PATH` for retrieval tests.

## Workflow

1. Open an issue first for anything non-trivial; discuss before coding.
2. Fork → branch (`feature/<slug>` or `fix/<slug>`) → PR against `master`.
3. Keep commits atomic and the subject line under 72 characters.
4. Run `pytest` and `pyrefly check src/` locally before pushing.

## Pull requests

- One logical change per PR.
- Reference the related issue in the PR description (`Closes #N`).
- Add or update tests for any changed behaviour.
- Do not bump the version in `pyproject.toml`; maintainers do that on release.

## Code style

- Python 3.11+, fully type-hinted.
- No external formatter is enforced; match the surrounding style.
- Minimal, pinned dependencies — discuss in an issue before adding any new dep.

## Reporting bugs and requesting features

Use the GitHub issue templates:
- **Bug report** — `.github/ISSUE_TEMPLATE/bug.md`
- **Feature request** — `.github/ISSUE_TEMPLATE/feature.md`

For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
By participating you agree to abide by its terms.
