# Contributing

1. Create a focused branch and keep synthetic-data and human-oversight boundaries intact.
2. Install with `python -m pip install -e ".[dev]"`.
3. Run `make verify` before opening a pull request.
4. Add tests for new scenarios, configuration validations and adverse edge cases.
5. Document whether every new field is synthetic, official public context or derived analytics.

Scenario changes must include a rationale, internal parameter definition, expected false-positive impact, validation evidence and rollback plan. Never add real personal data or describe an alert as proof of wrongdoing.
