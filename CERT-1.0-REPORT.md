# retryheader 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to retryheader. PyPI has 0.2.1, which is
byte for byte the `main` branch at 37aa903 (the wheel's modules compared with the tree), so
every change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (37aa903, same code as PyPI 0.2.1)
- [x] Baseline gates on 0.2.1
- [x] Ground truth fetched live (item 7)
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, oracle, fuzz and hostile tests (items 6, 7, 9)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.1, every Python (items 8, 10, 13, 14)
- [ ] Author mutation round (item 18)
- [ ] Gates (item 15)
- [ ] PR and trace guard
- [ ] Five QA lenses (item 19) and independent review (item 16): run after this stage
