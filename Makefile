# ────────────────────────────────────────────────────────────────
# GalaxyCoils Zernio — Quick Reference
# ────────────────────────────────────────────────────────────────
#  make schedule       Schedule 5 posts/day for open slots
#  make schedule-dry   Preview what would be scheduled
#  make fill-gaps      Fill up to 10 schedule gaps
#  make fill-gaps-dry  Preview gap-fill without creating
#  make verify         Full queue health check (fails on duplicates/overlap)
#  make audit          Syntax-check ALL .py files + verify queue
#  make test           Run the full unit-test suite (auto-discovered)
#  make coverage       Tests + branch coverage report (fails under 95%)
#  make lint           Ruff lint (zero-error gate)
#  make typecheck      Mypy type check (zero-error gate)
#  make analytics      Engagement report by caption category
#  make dedup-dry      Preview duplicate posts
#  make dedup          Delete duplicate scheduled posts
#  make empties-dry    Preview excess empty-caption fixes (mix-protected)
#  make empties        Fix excess empty captions (keeps intentional ~30%)
#  make full-audit     audit + lint + typecheck + coverage (CI gate)
# ────────────────────────────────────────────────────────────────

.PHONY: help schedule schedule-dry fill-gaps fill-gaps-dry \
        verify audit test coverage lint typecheck \
        dedup-dry dedup empties-dry empties full-audit analytics

# ── Scheduling ─────────────────────────────────────────────────

schedule:
	python3 schedule_5_per_day.py

schedule-dry:
	python3 schedule_5_per_day.py --dry-run

fill-gaps:
	python3 fill_schedule_gaps.py

fill-gaps-dry:
	python3 fill_schedule_gaps.py --dry-run

# ── Analytics ──────────────────────────────────────────────────

analytics:
	python3 scripts/analyze_engagement.py

# ── Verification ───────────────────────────────────────────────

verify:
	python3 scripts/verify_queue.py

# Syntax-check every tracked .py file — self-maintaining, can never
# drift from the actual file inventory (previously a hardcoded list
# that silently missed new files like analyze_engagement.py).
audit:
	@echo "=== Syntax check (all .py files) ==="
	@fail=0; \
	for f in $$(find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' | sort); do \
	  python3 -m py_compile "$$f" && echo "  OK: $$f" || { echo "  FAIL: $$f"; fail=1; }; \
	done; \
	exit $$fail
	@echo ""
	@echo "=== Queue health ==="
	@python3 scripts/verify_queue.py

# ── Quality gate ───────────────────────────────────────────────

lint:
	ruff check .

typecheck:
	mypy

coverage:
	python3 -m coverage run -m unittest discover -s scripts -t . -p "test_*.py"
	python3 -m coverage report

# ── Dedup & Maintenance ────────────────────────────────────────

dedup-dry:
	python3 purge_zernio_duplicates.py --dry-run

dedup:
	python3 purge_zernio_duplicates.py

# Empties maintenance is mix-protected: update_empty_posts.py only acts
# when empties exceed --max-empty-ratio (default 35%) of the queue, and
# only fixes enough posts to return to the intentional ~30% (PLAN.md).
empties-dry:
	python3 scripts/update_empty_posts.py --dry-run

empties:
	python3 scripts/update_empty_posts.py

# ── Testing ────────────────────────────────────────────────────
# Suites are auto-discovered (scripts/test_*.py) — adding a test file
# requires zero Makefile changes.

test:
	python3 -m unittest discover -s scripts -t . -p "test_*.py" -v

# ── Full Audit (pre-push hook + CI) ────────────────────────────

full-audit: audit lint typecheck coverage

# ── Help ───────────────────────────────────────────────────────

help:
	@echo "GalaxyCoils Zernio — Quick Reference"
	@echo ""
	@echo "Scheduling:"
	@echo "  make schedule         Schedule 5 posts/day for open slots"
	@echo "  make schedule-dry     Preview what would be scheduled"
	@echo "  make fill-gaps        Fill up to 10 schedule gaps"
	@echo "  make fill-gaps-dry    Preview gap-fill without creating"
	@echo ""
	@echo "Verification & Quality:"
	@echo "  make verify           Queue health check (exit 1 on duplicates/overlap)"
	@echo "  make audit            Syntax-check ALL .py files + verify"
	@echo "  make lint             Ruff lint"
	@echo "  make typecheck        Mypy type check"
	@echo "  make coverage         Tests + coverage (fails under 95%)"
	@echo ""
	@echo "Dedup & Maintenance:"
	@echo "  make dedup-dry        Preview duplicate posts (no deletes)"
	@echo "  make dedup            Delete duplicate scheduled posts"
	@echo "  make empties-dry      Preview excess empty-caption fixes"
	@echo "  make empties          Fix excess empties (protects intentional ~30%)"
	@echo ""
	@echo "Analytics:"
	@echo "  make analytics        Engagement report by caption category"
	@echo ""
	@echo "Full Audit:"
	@echo "  make full-audit       audit + lint + typecheck + coverage"
	@echo ""
	@echo "See MEMORY.md for architecture, PERFECTION.md for the perfection roadmap."
