# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
python scripts/fetch_upstream.py
```

The fetch step is optional: it downloads the third-party files listed in
`tests/upstream/MANIFEST.json` (RFC 9110, RFC 9651, RFC 5322 and one of its errata, the
RateLimit draft, the HTTP working group's structured field test suite), each checked
against its sha256, into a folder that git ignores. The tests that need them skip until
they are there. The oracle tests also use `http-sf`, `werkzeug`, `urllib3`, `requests`,
`httpx` and `multidict` when they are installed; none of them is a dependency.

## Before you open a pull request

- Keep public API in `src/retryheader/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes. The
  comments at its top list the optional end-to-end and upgrade checks.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
