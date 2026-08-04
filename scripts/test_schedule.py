"""
Unit tests for schedule_5_per_day.py core functions:
  - choose_video_url — pure: resolution ranking, edge cases
  - generate_caption_plan — distribution: empty/micro/value/CTA counts
  - open_slots — slot generation: empty, partial, full, days_ahead, past exclusion
  - fetch_unique_urls — URL fetching: limit, seen-skip, intra-batch dedup, exhaustion
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import schedule_5_per_day


# Sample Pexels video fixtures
def _video(url, height=1080, width=1920):
    return {
        "video_files": [{"link": url, "height": height, "width": width}],
    }

def _video_multi(*files):
    """video with multiple file options: [(url, height, width), ...]"""
    return {
        "video_files": [{"link": u, "height": h, "width": w} for u, h, w in files],
    }


# ═══════════════════════════════════════════════════════════════
# choose_video_url
# ═══════════════════════════════════════════════════════════════
class TestChooseVideoURL(unittest.TestCase):
    def test_single_file(self):
        url = schedule_5_per_day.choose_video_url(_video("https://a.mp4"))
        self.assertEqual(url, "https://a.mp4")

    def test_closest_to_1920_height(self):
        """1080 (diff=840) beats 720 (diff=1200)."""
        v = _video_multi(("720.mp4", 720, 1280), ("1080.mp4", 1080, 1920))
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "1080.mp4")

    def test_same_height_larger_resolution_wins(self):
        """Both 1080 tall; 1920×1080 beats 640×1080 on tiebreaker.
        Primary key (distance to 1920): both 840.
        Secondary key (-min(h,w)): -1080 vs -640 → 1920×1080 wins."""
        v = _video_multi(("small.mp4", 1080, 640), ("big.mp4", 1080, 1920))
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "big.mp4")

    def test_no_video_files(self):
        self.assertEqual(schedule_5_per_day.choose_video_url({}), "")

    def test_empty_video_files(self):
        v = {"video_files": []}
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "")

    def test_files_without_link_skipped(self):
        v = {
            "video_files": [
                {"height": 1080, "width": 1920},          # no link
                {"link": "good.mp4", "height": 720, "width": 1280},
            ]
        }
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "good.mp4")

    def test_all_files_without_link(self):
        v = {
            "video_files": [
                {"height": 1080}, {"width": 1920},
            ]
        }
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "")

    def test_4k_beats_1080p(self):
        """2160 (diff=240) beats 1080 (diff=840) — 4K is closer to 1920."""
        v = _video_multi(("1080.mp4", 1080, 1920), ("4k.mp4", 2160, 3840))
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "4k.mp4")

    def test_null_height_treated_as_zero(self):
        """Height=None → 0, diff=1920 (worst)."""
        v = _video_multi(("null_h.mp4", None, 1920), ("good.mp4", 1080, 1920))
        self.assertEqual(schedule_5_per_day.choose_video_url(v), "good.mp4")


# ═══════════════════════════════════════════════════════════════
# generate_caption_plan
# ═══════════════════════════════════════════════════════════════
class TestGenerateCaptionPlan(unittest.TestCase):
    def test_zero_total(self):
        self.assertEqual(schedule_5_per_day.generate_caption_plan(0), [])

    def test_length_matches_total(self):
        for n in [1, 3, 10, 50]:
            self.assertEqual(len(schedule_5_per_day.generate_caption_plan(n)), n)

    def test_known_totals_match_expected_distribution(self):
        """Verify engagement pivot distribution (30/30/22/18).
        total=50: empty=round(15)=15, micro=round(11)=11, value=round(9)=9, cta=15"""
        plan = schedule_5_per_day.generate_caption_plan(50)
        empty = sum(1 for c in plan if c == "")
        non_empty = [c for c in plan if c]
        self.assertEqual(empty, 15)
        self.assertEqual(len(non_empty), 35)  # 11+9+15

    def test_small_total(self):
        """total=2: empty=round(0.6)=1, micro=round(0.44)=0, value=round(0.36)=0, cta=1"""
        plan = schedule_5_per_day.generate_caption_plan(2)
        self.assertEqual(len(plan), 2)
        empty = sum(1 for c in plan if c == "")
        self.assertEqual(empty, 1)

    def test_all_non_empty_from_known_pools(self):
        """Every non-empty caption comes from MICRO_HOOKS, VALUE_CAPTIONS, or CTA_CAPTIONS."""
        known = (
            set(schedule_5_per_day.MICRO_HOOKS) |
            set(schedule_5_per_day.VALUE_CAPTIONS) |
            set(schedule_5_per_day.CTA_CAPTIONS)
        )
        plan = schedule_5_per_day.generate_caption_plan(100)
        for c in plan:
            if c:
                self.assertIn(c, known, f"Unexpected caption: {c!r}")

    def test_large_total_approximate_distribution(self):
        """With total=1000, counts should be within ±5 of expected (30/30/22/18)."""
        plan = schedule_5_per_day.generate_caption_plan(1000)
        empty = sum(1 for c in plan if c == "")
        micro = sum(1 for c in plan if c in schedule_5_per_day.MICRO_HOOKS)
        value = sum(1 for c in plan if c in schedule_5_per_day.VALUE_CAPTIONS)
        cta = sum(1 for c in plan if c in schedule_5_per_day.CTA_CAPTIONS)

        # expected: empty=300, micro=220, value=180, cta=300
        self.assertAlmostEqual(empty, 300, delta=5)
        self.assertAlmostEqual(micro, 220, delta=5)
        self.assertAlmostEqual(value, 180, delta=5)
        self.assertAlmostEqual(cta,   300, delta=5)


# ═══════════════════════════════════════════════════════════════
# open_slots
# ═══════════════════════════════════════════════════════════════
FROZEN_NOW = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)  # 09:00 UTC
SLOTS = [10, 13, 16, 19, 22]  # 5 slots/day


class TestOpenSlots(unittest.TestCase):
    def _mock_now(self):
        return FROZEN_NOW

    def _fake_list_scheduled(self, posts=None):
        """Return a mock for list_scheduled that returns the given posts."""
        def fake():
            return posts or []
        return fake

    def test_no_scheduled_posts_all_slots_returned(self):
        """With no scheduled posts, all 55 slots (11 days × 5) should be open."""
        # day 0: 10,13,16,19,22; days 1-10: same × 10 = 50; total 55
        with mock.patch("schedule_5_per_day.list_scheduled", return_value=[]), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = FROZEN_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)  # keep constructor
            # datetime constructor needs to work for building slot timestamps
            slots = schedule_5_per_day.open_slots(days_ahead=10)

        self.assertEqual(len(slots), 55)
        # First slot: day 0, hour 10
        self.assertEqual(slots[0], "2026-06-01T10:00:00.000Z")

    def test_partially_occupied(self):
        occupied = [
            {"scheduledFor": "2026-06-01T10:00:00.000Z"},
            {"scheduledFor": "2026-06-01T13:00:00.000Z"},
        ]
        with mock.patch("schedule_5_per_day.list_scheduled", return_value=occupied), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = FROZEN_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            slots = schedule_5_per_day.open_slots(days_ahead=10)

        self.assertEqual(len(slots), 53)  # 55 - 2 occupied
        self.assertNotIn("2026-06-01T10:00:00.000Z", slots)
        self.assertNotIn("2026-06-01T13:00:00.000Z", slots)

    def test_fully_occupied(self):
        """All 55 slots occupied → empty list."""
        all_iso = []
        day0 = FROZEN_NOW.date()
        for d in range(11):
            day = day0 + timedelta(days=d)
            for h in SLOTS:
                dt = datetime(day.year, day.month, day.day, h, 0, 0, tzinfo=timezone.utc)
                if dt > FROZEN_NOW:
                    all_iso.append({"scheduledFor": dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")})

        with mock.patch("schedule_5_per_day.list_scheduled", return_value=all_iso), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = FROZEN_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            slots = schedule_5_per_day.open_slots(days_ahead=10)

        self.assertEqual(slots, [])

    def test_days_ahead_respected(self):
        """days_ahead=1 → only day 0 + day 1 = 10 slots."""
        with mock.patch("schedule_5_per_day.list_scheduled", return_value=[]), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = FROZEN_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            slots = schedule_5_per_day.open_slots(days_ahead=1)

        self.assertEqual(len(slots), 10)

    def test_past_slots_excluded(self):
        """If 'now' is 14:00, the 10:00 and 13:00 slots on day 0 are excluded."""
        now_14 = datetime(2026, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
        with mock.patch("schedule_5_per_day.list_scheduled", return_value=[]), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = now_14
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            slots = schedule_5_per_day.open_slots(days_ahead=10)

        # Day 0 has only 16, 19, 22 (3 slots), days 1-10 have 50 → 53 total
        self.assertEqual(len(slots), 53)
        self.assertNotIn("2026-06-01T10:00:00.000Z", slots)
        self.assertNotIn("2026-06-01T13:00:00.000Z", slots)

    def test_none_scheduled_for_ignored(self):
        """Posts with scheduledFor=None don't crash and don't occupy slots."""
        occupied = [{"scheduledFor": None}]
        with mock.patch("schedule_5_per_day.list_scheduled", return_value=occupied), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = FROZEN_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            slots = schedule_5_per_day.open_slots(days_ahead=10)

        self.assertEqual(len(slots), 55)


# ═══════════════════════════════════════════════════════════════
# fetch_unique_urls
# ═══════════════════════════════════════════════════════════════
def _pexels_response(*video_ids):
    """Build a Pexels API response with one video per ID."""
    videos = []
    for vid in video_ids:
        videos.append({
            "video_files": [
                {"link": f"https://cdn.pexels.com/video-files/{vid}/hd.mp4",
                 "height": 1080, "width": 1920}
            ]
        })
    return mock.Mock(**{"json.return_value": {"videos": videos}, "raise_for_status": mock.Mock()})


class TestFetchUniqueURLs(unittest.TestCase):
    def test_returns_correct_limit(self):
        with mock.patch("schedule_5_per_day.get_all_seen_source_ids", return_value=set()), \
             mock.patch("schedule_5_per_day.requests.get",
                        return_value=_pexels_response(111, 222)):
            urls = schedule_5_per_day.fetch_unique_urls(limit=2)
        self.assertEqual(len(urls), 2)

    def test_skips_seen_ids(self):
        seen = {"111"}  # 111 already used
        with mock.patch("schedule_5_per_day.get_all_seen_source_ids", return_value=seen), \
             mock.patch("schedule_5_per_day.requests.get",
                        return_value=_pexels_response(111, 222, 333)):
            urls = schedule_5_per_day.fetch_unique_urls(limit=2)

        self.assertEqual(len(urls), 2)
        self.assertNotIn("https://cdn.pexels.com/video-files/111/hd.mp4", urls)

    def test_skips_intra_batch_duplicates(self):
        """Two videos with the same ID in one response — only first kept."""
        with mock.patch("schedule_5_per_day.get_all_seen_source_ids", return_value=set()), \
             mock.patch("schedule_5_per_day.requests.get",
                        return_value=_pexels_response(444, 444, 555)):
            urls = schedule_5_per_day.fetch_unique_urls(limit=3)

        # Only 2 unique: 444 and 555
        self.assertEqual(len(urls), 2)

    def test_exhaustion_returns_whats_available(self):
        """Query pool exhausted before limit reached."""
        with mock.patch("schedule_5_per_day.get_all_seen_source_ids", return_value=set()), \
             mock.patch("schedule_5_per_day.requests.get",
                        # Return just 1 video per query, 8 queries total → 8 unique
                        side_effect=[_pexels_response(i) for i in range(100, 108)]):
            urls = schedule_5_per_day.fetch_unique_urls(limit=20)

        self.assertEqual(len(urls), 8)  # QUERY_POOL has 8 entries

    def test_urls_in_correct_format(self):
        with mock.patch("schedule_5_per_day.get_all_seen_source_ids", return_value=set()), \
             mock.patch("schedule_5_per_day.requests.get",
                        return_value=_pexels_response(777)):
            urls = schedule_5_per_day.fetch_unique_urls(limit=1)

        self.assertIn("video-files/777/", urls[0])

    def test_skips_videos_without_extractable_id(self):
        """Video with no video-files/NNN/ pattern in URL → skipped."""
        bad_video = {
            "video_files": [
                {"link": "https://example.com/not-a-pexels-url/image.jpg",
                 "height": 1080, "width": 1920}
            ]
        }
        good_video = {
            "video_files": [
                {"link": "https://cdn.pexels.com/video-files/888/hd.mp4",
                 "height": 1080, "width": 1920}
            ]
        }
        response = mock.Mock(**{
            "json.return_value": {"videos": [bad_video, good_video]},
            "raise_for_status": mock.Mock(),
        })

        with mock.patch("schedule_5_per_day.get_all_seen_source_ids", return_value=set()), \
             mock.patch("schedule_5_per_day.requests.get", return_value=response):
            urls = schedule_5_per_day.fetch_unique_urls(limit=2)

        self.assertEqual(len(urls), 1)
        self.assertIn("888", urls[0])


# ═══════════════════════════════════════════════════════════════
# open_slots — ISO format robustness (double-booking regression)
# ═══════════════════════════════════════════════════════════════
class TestOpenSlotsIsoFormats(unittest.TestCase):
    """The old string-equality check missed occupied slots when the API
    returned a different-but-equal timestamp format → double-booking risk."""

    def _slots_with_occupied(self, occupied):
        with mock.patch("schedule_5_per_day.list_scheduled", return_value=occupied), \
             mock.patch("schedule_5_per_day.datetime") as mock_dt:
            mock_dt.now.return_value = FROZEN_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            return schedule_5_per_day.open_slots(days_ahead=10)

    def test_z_suffix_without_millis_still_occupied(self):
        occupied = [{"scheduledFor": "2026-06-01T10:00:00Z"}]
        slots = self._slots_with_occupied(occupied)
        self.assertEqual(len(slots), 54)
        self.assertNotIn("2026-06-01T10:00:00.000Z", slots)

    def test_explicit_offset_still_occupied(self):
        occupied = [{"scheduledFor": "2026-06-01T10:00:00+00:00"}]
        slots = self._slots_with_occupied(occupied)
        self.assertNotIn("2026-06-01T10:00:00.000Z", slots)

    def test_fractional_seconds_still_occupied(self):
        occupied = [{"scheduledFor": "2026-06-01T10:00:00.123456Z"}]
        slots = self._slots_with_occupied(occupied)
        # 10:00:00.123 != 10:00:00.000 — close but distinct instant; slot stays open.
        # (A post AT the slot second exact is covered by the cases above.)
        self.assertIn("2026-06-01T10:00:00.000Z", slots)

    def test_unparseable_timestamp_ignored(self):
        occupied = [{"scheduledFor": "not-a-date"}, {"scheduledFor": ""}]
        slots = self._slots_with_occupied(occupied)
        self.assertEqual(len(slots), 55)


class TestParseIso(unittest.TestCase):
    def test_z_suffix(self):
        dt = schedule_5_per_day._parse_iso("2026-06-01T10:00:00.000Z")
        self.assertEqual(dt, datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc))

    def test_naive_assumed_utc(self):
        dt = schedule_5_per_day._parse_iso("2026-06-01T10:00:00")
        self.assertEqual(dt, datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc))

    def test_offset_normalized_to_utc(self):
        dt = schedule_5_per_day._parse_iso("2026-06-01T12:00:00+02:00")
        self.assertEqual(dt, datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc))

    def test_garbage_returns_none(self):
        for bad in (None, "", "nope", "2026-13-99T99:99"):
            self.assertIsNone(schedule_5_per_day._parse_iso(bad))


# ═══════════════════════════════════════════════════════════════
# search_pexels — retry/backoff
# ═══════════════════════════════════════════════════════════════
class TestSearchPexels(unittest.TestCase):
    def test_success_first_try(self):
        with mock.patch("schedule_5_per_day.requests.get",
                        return_value=_pexels_response(1, 2, 3)) as get:
            videos = schedule_5_per_day.search_pexels("drone")
        self.assertEqual(len(videos), 3)
        self.assertEqual(get.call_count, 1)

    def test_retries_on_request_exception(self):
        import requests as real_requests
        ok = _pexels_response(7)
        with mock.patch("schedule_5_per_day.requests.get",
                        side_effect=[real_requests.ConnectionError("down"), ok]), \
             mock.patch("schedule_5_per_day.time.sleep") as sleep:
            videos = schedule_5_per_day.search_pexels("drone")
        self.assertEqual(len(videos), 1)
        sleep.assert_called_once_with(5)

    def test_exhaustion_raises_runtime_error(self):
        import requests as real_requests
        with mock.patch("schedule_5_per_day.requests.get",
                        side_effect=real_requests.Timeout("t")), \
             mock.patch("schedule_5_per_day.time.sleep"), self.assertRaises(RuntimeError):
            schedule_5_per_day.search_pexels("drone", max_retries=2)


# ═══════════════════════════════════════════════════════════════
# create_post / main
# ═══════════════════════════════════════════════════════════════
class TestCreatePost(unittest.TestCase):
    def test_success_records_history(self):
        url = "https://cdn.pexels.com/video-files/4242/hd.mp4"
        with mock.patch("schedule_5_per_day._create_post", return_value=True), \
             mock.patch("schedule_5_per_day.record_scheduled") as record:
            schedule_5_per_day.create_post(url, "cap", "2026-06-01T10:00:00.000Z")
        record.assert_called_once_with("4242")

    def test_failure_raises(self):
        with mock.patch("schedule_5_per_day._create_post", return_value=False), self.assertRaises(RuntimeError):
            schedule_5_per_day.create_post("https://x/video-files/1/a.mp4", "", "2026-06-01T10:00:00.000Z")


class TestRunJson(unittest.TestCase):
    def test_raises_on_nonzero_exit(self):
        proc = mock.Mock(returncode=1, stdout="out", stderr="err")
        with mock.patch("schedule_5_per_day.subprocess.run", return_value=proc), \
             self.assertRaises(RuntimeError):
            schedule_5_per_day.run_json(["zernio"])

    def test_list_scheduled_parses_posts(self):
        with mock.patch("schedule_5_per_day.run_json", return_value={"posts": [{"_id": "p1"}]}):
            self.assertEqual(schedule_5_per_day.list_scheduled(), [{"_id": "p1"}])


class TestDotEnvLoader(unittest.TestCase):
    """The import-time .env loader. Skipped when a real .env exists so we
    never clobber local secrets."""

    def test_env_file_loaded(self):
        import importlib
        repo_root = Path(__file__).resolve().parent.parent
        env_path = repo_root / ".env"
        if env_path.exists():
            self.skipTest("real .env present — not touching it")
        try:
            env_path.write_text("# comment\nTEST_DOTENV_KEY=some=value\nEMPTY_LINE_OK\n\n")
            os.environ.pop("TEST_DOTENV_KEY", None)
            importlib.reload(schedule_5_per_day)
            self.assertEqual(os.environ.get("TEST_DOTENV_KEY"), "some=value")
        finally:
            os.environ.pop("TEST_DOTENV_KEY", None)
            env_path.unlink(missing_ok=True)
            importlib.reload(schedule_5_per_day)


class TestZernioGuardPostUtils(unittest.TestCase):
    def test_create_post_returns_false_without_zernio(self):
        from scripts import post_utils
        with mock.patch.object(post_utils, "ZERNI0", ""):
            self.assertFalse(post_utils.create_post("https://x/video-files/1/a.mp4", "cap", "2026-06-01T10:00:00.000Z"))


class TestMain(unittest.TestCase):
    def test_missing_api_key_exits(self):
        with mock.patch.object(schedule_5_per_day, "PEXELS_API_KEY", None), \
             mock.patch("sys.argv", ["schedule_5_per_day.py"]), self.assertRaises(SystemExit) as ctx:
            schedule_5_per_day.main()
        self.assertIn("PEXELS_API_KEY", str(ctx.exception))

    def test_dry_run_does_not_need_api_key(self):
        with mock.patch.object(schedule_5_per_day, "PEXELS_API_KEY", None), \
             mock.patch("schedule_5_per_day.open_slots", return_value=["2026-06-01T10:00:00.000Z"]), \
             mock.patch("schedule_5_per_day.fetch_unique_urls") as fetch, \
             mock.patch("sys.argv", ["schedule_5_per_day.py", "--dry-run"]):
            schedule_5_per_day.main()
        fetch.assert_not_called()

    def test_no_open_slots_early_return(self):
        with mock.patch("schedule_5_per_day.open_slots", return_value=[]), \
             mock.patch("sys.argv", ["schedule_5_per_day.py", "--dry-run"]):
            schedule_5_per_day.main()  # no exception

    def test_schedules_slots(self):
        slots = ["2026-06-01T10:00:00.000Z", "2026-06-01T13:00:00.000Z"]
        urls = ["https://x/video-files/1/a.mp4", "https://x/video-files/2/b.mp4"]
        with mock.patch.object(schedule_5_per_day, "PEXELS_API_KEY", "k"), \
             mock.patch("schedule_5_per_day.open_slots", return_value=slots), \
             mock.patch("schedule_5_per_day.fetch_unique_urls", return_value=urls), \
             mock.patch("schedule_5_per_day.create_post") as create, \
             mock.patch("schedule_5_per_day.time.sleep"), \
             mock.patch("sys.argv", ["schedule_5_per_day.py"]):
            schedule_5_per_day.main()
        self.assertEqual(create.call_count, 2)

    def test_insufficient_urls_raises(self):
        with mock.patch.object(schedule_5_per_day, "PEXELS_API_KEY", "k"), \
             mock.patch("schedule_5_per_day.open_slots", return_value=["2026-06-01T10:00:00.000Z"]), \
             mock.patch("schedule_5_per_day.fetch_unique_urls", return_value=[]), \
             mock.patch("sys.argv", ["schedule_5_per_day.py"]), self.assertRaises(RuntimeError):
            schedule_5_per_day.main()


if __name__ == "__main__":
    unittest.main()
