# ────────────────────────────────────────────────────────────────
# GalaxyCoils Zernio — Quick Reference
# ────────────────────────────────────────────────────────────────
#  make schedule       Schedule 5 posts/day for open slots
#  make schedule-dry   Preview what would be scheduled
#  make fill-gaps      Fill up to 10 schedule gaps
#  make fill-gaps-dry  Preview gap-fill without creating
#  make verify         Full queue health check
#  make audit          Syntax-check all 17 .py files + verify queue
#  make test           Run all 78 unit tests
#  make test-secure    Run secure_dedup tests (18)
#  make test-post      Run post_utils tests (15)
#  make test-purge     Run purge_dedup tests (10)
#  make test-gaps      Run fill_gaps tests (8)
#  make test-schedule  Run schedule tests (27)
#  make dedup-dry      Preview duplicate posts
#  make dedup          Delete duplicate scheduled posts
#  make empties-dry    Preview empty-caption posts
#  make empties        Fix empty-caption posts
#  make full-audit     Syntax + verify + all 78 tests (17 files)
# ────────────────────────────────────────────────────────────────

.PHONY: help schedule schedule-dry fill-gaps fill-gaps-dry \
        verify audit test test-secure test-post test-purge test-gaps test-schedule \
        dedup-dry dedup empties-dry empties full-audit

# ── Scheduling ─────────────────────────────────────────────────

schedule:
	python3 schedule_5_per_day.py

schedule-dry:
	python3 schedule_5_per_day.py --dry-run

fill-gaps:
	python3 fill_schedule_gaps.py

fill-gaps-dry:
	python3 fill_schedule_gaps.py --dry-run

# ── Verification ───────────────────────────────────────────────

verify:
	python3 scripts/verify_queue.py

audit:
	@echo "=== Syntax check ==="
	@for f in \
	  purge_zernio_duplicates.py fill_schedule_gaps.py schedule_5_per_day.py \
	  scripts/batch_recover.py scripts/rebuild_viral_queue.py \
	  scripts/captions_pool.py scripts/chunk_recover.py scripts/secure_dedup.py \
	  scripts/verify_queue.py scripts/recover_rebuild.py scripts/post_utils.py \
	  scripts/update_empty_posts.py \
	  scripts/test_secure_dedup.py scripts/test_post_utils.py scripts/test_purge_dedup.py \
	  scripts/test_fill_gaps.py scripts/test_schedule.py; \
	do \
	  python3 -m py_compile "$$f" && echo "  OK: $$f" || echo "  FAIL: $$f"; \
	done
	@echo ""
	@echo "=== Queue health ==="
	@python3 scripts/verify_queue.py

# ── Dedup & Maintenance ────────────────────────────────────────

dedup-dry:
	python3 purge_zernio_duplicates.py --dry-run

dedup:
	python3 purge_zernio_duplicates.py

empties-dry:
	python3 scripts/update_empty_posts.py --dry-run --min-empty 3

empties:
	python3 scripts/update_empty_posts.py --min-empty 3

# ── Testing ────────────────────────────────────────────────────

test:
	python3 -m unittest scripts.test_secure_dedup \
	                       scripts.test_post_utils \
	                       scripts.test_purge_dedup \
	                       scripts.test_fill_gaps \
	                       scripts.test_schedule -v

test-secure:
	python3 -m unittest scripts.test_secure_dedup -v

test-post:
	python3 -m unittest scripts.test_post_utils -v

test-purge:
	python3 -m unittest scripts.test_purge_dedup -v

test-gaps:
	python3 -m unittest scripts.test_fill_gaps -v

test-schedule:
	python3 -m unittest scripts.test_schedule -v

# ── Full Audit ─────────────────────────────────────────────────

full-audit: audit test

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
	@echo "Verification:"
	@echo "  make verify           Full queue health check"
	@echo "  make audit            Syntax-check all .py files + verify"
	@echo ""
	@echo "Dedup & Maintenance:"
	@echo "  make dedup-dry        Preview duplicate posts (no deletes)"
	@echo "  make dedup            Delete duplicate scheduled posts"
	@echo "  make empties-dry      Preview empty-caption posts (threshold 3)"
	@echo "  make empties          Fix empty-caption posts (threshold 3)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all 78 unit tests"
	@echo "  make test-secure      secure_dedup tests (18)"
	@echo "  make test-post        post_utils tests (15)"
	@echo "  make test-purge       purge_dedup tests (10)"
	@echo "  make test-gaps        fill_gaps tests (8)"
	@echo "  make test-schedule    schedule_5_per_day tests (27)"
	@echo ""
	@echo "Full Audit:"
	@echo "  make full-audit       Syntax + verify + all 78 tests"
	@echo ""
	@echo "See MEMORY.md for architecture details and current queue state."
