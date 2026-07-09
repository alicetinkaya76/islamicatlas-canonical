# islamicatlas-canonical — quick command layer (H9 Stage 4).
# The weekly gate is `make test`; CI runs the same target (single source of truth).

.PHONY: test test-fast schema reindex-dry scrape-status help

help:
	@echo "make test          - full gate: schema fixtures CLI + projector + resolver + pytest (~25 s with store)"
	@echo "make test-fast     - inner loop: pytest without the whole-store validation tests (~9 s)"
	@echo "make schema        - 15 schema fixture checks (also inside pytest as test_schema_fixtures)"
	@echo "make reindex-dry   - project all 46K canonical records (search-layer regression gate)"
	@echo "make scrape-status - dia-tdv-scrape checkpoint progress"

test:
	python3 tests/run_schema_tests.py
	python3 tests/test_projector.py
	python3 tests/test_resolver.py
	python3 -m pytest tests/integration -q

test-fast:
	python3 -m pytest tests/integration -q -m "not slow_fullstore"

schema:
	python3 tests/run_schema_tests.py

reindex-dry:
	python3 pipelines/search/full_reindex.py --dry-run --quiet

scrape-status:
	python3 pipelines/adapters/dia_tdv_scrape/scrape.py --status
