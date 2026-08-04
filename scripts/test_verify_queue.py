"""
Unit tests for scripts/verify_queue.py:
  - health gate: exit 1 on duplicates or published overlap, 0 when healthy
  - --no-fail escape hatch
  - caption mix uses the shared pool-based classifier
  - per-day counting
"""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import verify_queue
from scripts.captions_pool import CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS


def _post(post_id, scheduled_for, content="", media_url=""):
    post = {"_id": post_id, "scheduledFor": scheduled_for, "content": content}
    if media_url:
        post["mediaItems"] = [{"url": media_url}]
    return post


def _run_main(scheduled, published_ids, argv=None):
    """Run verify_queue.main() with mocked fetches; return (exit_code, report)."""
    buf = io.StringIO()
    with mock.patch("scripts.verify_queue.fetch_posts", return_value=scheduled), \
         mock.patch("scripts.verify_queue.fetch_published_source_ids", return_value=published_ids), \
         mock.patch("sys.argv", ["verify_queue.py"] + (argv or [])), \
         redirect_stdout(buf):
        code = verify_queue.main()
    return code, json.loads(buf.getvalue())


class TestHealthGate(unittest.TestCase):
    def test_empty_queue_is_healthy(self):
        code, report = _run_main([], set())
        self.assertEqual(code, 0)
        self.assertTrue(report["healthy"])
        self.assertEqual(report["scheduled_total"], 0)

    def test_unique_queue_is_healthy(self):
        scheduled = [
            _post("a", "2026-06-01T10:00:00.000Z", media_url="https://x/video-files/111/hd.mp4"),
            _post("b", "2026-06-01T13:00:00.000Z", media_url="https://x/video-files/222/hd.mp4"),
        ]
        code, report = _run_main(scheduled, set())
        self.assertEqual(code, 0)
        self.assertTrue(report["healthy"])
        self.assertEqual(report["scheduled_duplicates"], {})

    def test_intra_queue_duplicates_fail(self):
        scheduled = [
            _post("a", "2026-06-01T10:00:00.000Z", media_url="https://x/video-files/111/hd.mp4"),
            _post("b", "2026-06-01T13:00:00.000Z", media_url="https://x/video-files/111/hd.mp4"),
        ]
        code, report = _run_main(scheduled, set())
        self.assertEqual(code, 1)
        self.assertFalse(report["healthy"])
        self.assertEqual(report["scheduled_duplicates"], {"111": 2})

    def test_published_overlap_fails(self):
        scheduled = [
            _post("a", "2026-06-01T10:00:00.000Z", media_url="https://x/video-files/999/hd.mp4"),
        ]
        code, report = _run_main(scheduled, {"999"})
        self.assertEqual(code, 1)
        self.assertEqual(len(report["published_overlap"]), 1)
        self.assertEqual(report["published_overlap"][0]["source_id"], "999")

    def test_no_fail_flag_always_exits_zero(self):
        scheduled = [
            _post("a", "2026-06-01T10:00:00.000Z", media_url="https://x/video-files/111/hd.mp4"),
            _post("b", "2026-06-01T13:00:00.000Z", media_url="https://x/video-files/111/hd.mp4"),
        ]
        code, report = _run_main(scheduled, set(), argv=["--no-fail"])
        self.assertEqual(code, 0)
        self.assertFalse(report["healthy"])  # report still truthful

    def test_posts_without_media_dont_crash(self):
        scheduled = [_post("a", "2026-06-01T10:00:00.000Z")]
        code, report = _run_main(scheduled, set())
        self.assertEqual(code, 0)
        self.assertEqual(report["scheduled_total"], 1)


class TestCaptionMixReporting(unittest.TestCase):
    def test_pool_captions_classify_into_their_own_categories(self):
        """Regression: CTAs like 'Rate this 1-10.' were misreported as micro-hooks
        by the old keyword classifier."""
        scheduled = [
            _post("e", "2026-06-01T10:00:00.000Z", content=""),
            _post("c", "2026-06-01T13:00:00.000Z", content=CTA_CAPTIONS[7]),    # "Rate this 1-10."
            _post("m", "2026-06-01T16:00:00.000Z", content=MICRO_HOOKS[1]),    # contains 'rate'
            _post("v", "2026-06-01T19:00:00.000Z", content=VALUE_CAPTIONS[0]),
        ]
        code, report = _run_main(scheduled, set())
        self.assertEqual(code, 0)
        mix = report["caption_mix"]
        self.assertEqual(mix.get("empty"), 1)
        self.assertEqual(mix.get("cta"), 1)
        self.assertEqual(mix.get("micro-hook"), 1)
        self.assertEqual(mix.get("value"), 1)
        self.assertNotIn("other", mix)

    def test_mix_percentages_reported(self):
        scheduled = [
            _post("e1", "2026-06-01T10:00:00.000Z", content=""),
            _post("c1", "2026-06-01T13:00:00.000Z", content=CTA_CAPTIONS[0]),
        ]
        _, report = _run_main(scheduled, set())
        self.assertEqual(report["caption_mix_pct"]["empty"], 50.0)
        self.assertEqual(report["caption_mix_pct"]["cta"], 50.0)
        self.assertIn("target_mix_pct", report)

    def test_per_day_counts(self):
        scheduled = [
            _post("a", "2026-06-01T10:00:00.000Z"),
            _post("b", "2026-06-01T13:00:00.000Z"),
            _post("c", "2026-06-02T10:00:00.000Z"),
        ]
        _, report = _run_main(scheduled, set())
        self.assertEqual(report["per_day"], {"2026-06-01": 2, "2026-06-02": 1})


if __name__ == "__main__":
    unittest.main()
