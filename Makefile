# islamicatlas-canonical — quick command layer (H9 Stage 4).
# The weekly gate is `make test`; CI runs the same target (single source of truth).

.PHONY: test test-fast schema reindex-dry scrape-status emit-collection upsert-live help

help:
	@echo "make test          - full gate: schema fixtures CLI + projector + resolver + pytest (~25 s with store)"
	@echo "make test-fast     - inner loop: pytest without the whole-store validation tests (~9 s)"
	@echo "make schema        - 17 schema fixture checks (also inside pytest as test_schema_fixtures)"
	@echo "make reindex-dry   - project all 46K canonical records (search-layer regression gate)"
	@echo "make scrape-status - dia-tdv-scrape checkpoint progress"
	@echo "make emit-collection - Typesense create-collection govdesi (stdout)"
	@echo "make upsert-live   - canli Typesense'e yukle (TYPESENSE_URL+API_KEY gerekli)"

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

emit-collection:
	python3 search/typesense_schema_emit.py

upsert-live:
	python3 pipelines/search/upsert.py

view-data:
	python3 pipelines/frontend/build_view_data.py --view all
	python3 pipelines/frontend/build_book_city_atlas.py
	python3 pipelines/frontend/build_canonical_map_layer.py
	python3 pipelines/_index/build_lookup.py --quiet
	python3 pipelines/frontend/build_alatli_synchronic.py
	python3 pipelines/frontend/build_scholar_network.py
	python3 pipelines/frontend/build_ulema_pool.py
	python3 pipelines/frontend/build_place_facets.py
	python3 pipelines/frontend/build_darp_pids.py
	python3 pipelines/frontend/build_person_clusters.py
	python3 pipelines/frontend/build_person_bridge.py
	python3 pipelines/frontend/build_ulema_pool_links.py
	python3 pipelines/frontend/build_causal_review.py
	python3 pipelines/frontend/build_canonical_overview.py
