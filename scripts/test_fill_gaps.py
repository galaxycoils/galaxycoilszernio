"""
Unit tests for fill_schedule_gaps.py's scheduling logic:
  - No open slots → exits early, no API calls
  - Dry-run → previews only, no create_post or fetch_unique_urls
  - Success path → creates posts, calls dependencies correctly
  - Insufficient URLs → raises RuntimeError
  - POSTS_TO_SCHEDULE capping → only uses first 10 slots
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fill_schedule_gaps

SAMPLE_SLOTS = [
    "2026-06-01T10:00:00.000Z",
    "2026-06-01T13:00:00.000Z",
    "2026-06-01T16:00:00.000Z",
]
SAMPLE_CAPTIONS = ["caption A", "caption B", "caption C"]
SAMPLE_URLS = ["https://cdn.pexels.com/video-files/111/hd.mp4",
               "https://cdn.pexels.com/video-files/222/hd.mp4",
               "https://cdn.pexels.com/video-files/333/hd.mp4"]


# ---------------------------------------------------------------------------
# Shared helper — mocks all deps of main() and captures side effects
# ---------------------------------------------------------------------------
def _run_gap_fill(slots, captions, urls, dry_run=False):
    """Run main() with all external deps mocked.

    Returns (created_posts: list, print_calls: list) so callers can
    assert on what was scheduled and what was printed.

    NOTE: patch targets are ``fill_schedule_gaps.<name>`` because the
    source file uses ``from schedule_5_per_day import ...`` — the
    imported names are local bindings in the ``fill_schedule_gaps`` module.
    """
    created = []
    prints = []

    def fake_open_slots(days_ahead=10):
        return list(slots)

    def fake_generate_caption_plan(total):
        return list(captions[:total])

    def fake_fetch_unique_urls(limit=None):
        return list(urls[:limit]) if limit else list(urls)

    def fake_create_post(url, caption, scheduled_at):
        created.append((url, caption, scheduled_at))

    def fake_print(*args, **kwargs):
        prints.append(" ".join(str(a) for a in args))

    with mock.patch("fill_schedule_gaps.open_slots", fake_open_slots), \
         mock.patch("fill_schedule_gaps.generate_caption_plan", fake_generate_caption_plan), \
         mock.patch("fill_schedule_gaps.fetch_unique_urls", fake_fetch_unique_urls), \
         mock.patch("fill_schedule_gaps.create_post", fake_create_post), \
         mock.patch("fill_schedule_gaps.print", fake_print), \
         mock.patch("argparse.ArgumentParser.parse_args",
                    return_value=mock.Mock(dry_run=dry_run)):
        fill_schedule_gaps.main()

    return created, prints


# ---------------------------------------------------------------------------
# No open slots
# ---------------------------------------------------------------------------
class TestNoSlots(unittest.TestCase):
    def test_no_open_slots_prints_and_exits(self):
        created, prints = _run_gap_fill([], [], [], dry_run=False)

        self.assertEqual(created, [])
        self.assertTrue(any("No open slots found" in p for p in prints))


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------
class TestDryRun(unittest.TestCase):
    def test_dry_run_previews_but_does_not_create(self):
        created, prints = _run_gap_fill(SAMPLE_SLOTS, SAMPLE_CAPTIONS, SAMPLE_URLS, dry_run=True)

        self.assertEqual(created, [])
        self.assertTrue(any("[DRY RUN] Would schedule 3 posts" in p for p in prints))
        self.assertTrue(any("2026-06-01T10:00:00.000Z" in p for p in prints))
        self.assertTrue(any("caption A" in p for p in prints))
        self.assertTrue(any("[DRY RUN] No posts created." in p for p in prints))

    def test_dry_run_no_open_slots(self):
        created, prints = _run_gap_fill([], [], [], dry_run=True)

        self.assertEqual(created, [])
        self.assertTrue(any("No open slots found" in p for p in prints))


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------
class TestSuccess(unittest.TestCase):
    def test_creates_posts_for_each_slot(self):
        created, prints = _run_gap_fill(SAMPLE_SLOTS, SAMPLE_CAPTIONS, SAMPLE_URLS, dry_run=False)

        self.assertEqual(len(created), 3)
        # Verify each post was created with correct slot/url/caption
        self.assertEqual(created[0], (SAMPLE_URLS[0], SAMPLE_CAPTIONS[0], SAMPLE_SLOTS[0]))
        self.assertEqual(created[1], (SAMPLE_URLS[1], SAMPLE_CAPTIONS[1], SAMPLE_SLOTS[1]))
        self.assertEqual(created[2], (SAMPLE_URLS[2], SAMPLE_CAPTIONS[2], SAMPLE_SLOTS[2]))
        self.assertTrue(any("Successfully scheduled 3 posts" in p for p in prints))


# ---------------------------------------------------------------------------
# Insufficient URLs
# ---------------------------------------------------------------------------
class TestInsufficientURLs(unittest.TestCase):
    def test_fewer_urls_than_slots_raises(self):
        urls = [SAMPLE_URLS[0]]  # only 1 URL for 3 slots
        with self.assertRaises(RuntimeError) as ctx:
            _run_gap_fill(SAMPLE_SLOTS, SAMPLE_CAPTIONS, urls, dry_run=False)
        self.assertIn("Only found 1 unique videos for 3 slots", str(ctx.exception))

    def test_url_count_matches_slot_count(self):
        """Same number of URLs as slots — should succeed."""
        created, prints = _run_gap_fill(SAMPLE_SLOTS, SAMPLE_CAPTIONS, SAMPLE_URLS, dry_run=False)
        self.assertEqual(len(created), 3)


# ---------------------------------------------------------------------------
# POSTS_TO_SCHEDULE capping
# ---------------------------------------------------------------------------
class TestCap(unittest.TestCase):
    def test_more_slots_than_post_to_schedule_uses_cap(self):
        """open_slots returns 15 slots, but only first 10 (POSTS_TO_SCHEDULE) used."""
        many_slots = [f"2026-06-0{i}T10:00:00.000Z" for i in range(1, 16)]  # 15 slots
        many_captions = [f"cap {i}" for i in range(15)]
        many_urls = [f"https://cdn.pexels.com/video-files/{i}/hd.mp4" for i in range(100, 115)]

        created, prints = _run_gap_fill(many_slots, many_captions, many_urls, dry_run=False)

        self.assertEqual(len(created), 10)
        self.assertTrue(any("Successfully scheduled 10 posts" in p for p in prints))

    def test_fewer_slots_than_cap_uses_all(self):
        """Only 3 slots available — all should be used (not padded)."""
        created, prints = _run_gap_fill(SAMPLE_SLOTS, SAMPLE_CAPTIONS, SAMPLE_URLS, dry_run=False)

        self.assertEqual(len(created), 3)


if __name__ == "__main__":
    unittest.main()
