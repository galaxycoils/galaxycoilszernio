"""
Unit tests for scripts/analyze_engagement.py:
  - summarize(): category bucketing (incl. micro-hook — missing in v1),
    averages, medians, small-sample reliability flag
  - write_reports(): Markdown + JSON outputs
  - main(): missing zernio / empty analytics / happy path
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import analyze_engagement
from scripts.captions_pool import CATEGORIES, CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS


def _post(content, er=0.0, views=0):
    return {"content": content, "analytics": {"engagementRate": er, "views": views}}


class TestSummarize(unittest.TestCase):
    def test_all_categories_present_with_zero_posts(self):
        summary = analyze_engagement.summarize([])
        self.assertEqual(set(summary), set(CATEGORIES))
        for cat in CATEGORIES:
            self.assertEqual(summary[cat]["count"], 0)
            self.assertFalse(summary[cat]["reliable"])

    def test_micro_hook_category_populated(self):
        """Regression: v1 had no micro-hook category — every micro-hook
        caption fell into 'other', making the pivot unmeasurable."""
        posts = [_post(MICRO_HOOKS[0], er=4.0, views=1000)]
        summary = analyze_engagement.summarize(posts)
        self.assertEqual(summary["micro-hook"]["count"], 1)
        self.assertEqual(summary["other"]["count"], 0)

    def test_category_bucketing_and_averages(self):
        posts = [
            _post("", er=3.0, views=100),                     # empty
            _post("", er=5.0, views=300),                     # empty
            _post(CTA_CAPTIONS[0], er=2.0, views=200),        # cta
            _post(MICRO_HOOKS[0], er=4.0, views=400),         # micro-hook
            _post(VALUE_CAPTIONS[0], er=6.0, views=600),      # value
        ]
        summary = analyze_engagement.summarize(posts)
        self.assertEqual(summary["empty"]["count"], 2)
        self.assertEqual(summary["empty"]["avg_er"], 4.0)
        self.assertEqual(summary["empty"]["avg_views"], 200.0)
        self.assertEqual(summary["cta"]["avg_er"], 2.0)
        self.assertEqual(summary["micro-hook"]["avg_er"], 4.0)
        self.assertEqual(summary["value"]["max_views"], 600)

    def test_median_er(self):
        posts = [_post("", er=e) for e in (1.0, 2.0, 100.0)]
        summary = analyze_engagement.summarize(posts)
        self.assertEqual(summary["empty"]["avg_er"], 34.333)
        self.assertEqual(summary["empty"]["median_er"], 2.0)

    def test_reliability_threshold(self):
        posts = [_post(CTA_CAPTIONS[0])] * analyze_engagement.MIN_SAMPLE
        summary = analyze_engagement.summarize(posts)
        self.assertTrue(summary["cta"]["reliable"])
        posts = posts[:-1]
        summary = analyze_engagement.summarize(posts)
        self.assertFalse(summary["cta"]["reliable"])

    def test_missing_analytics_treated_as_zero(self):
        summary = analyze_engagement.summarize([{"content": ""}])
        self.assertEqual(summary["empty"]["count"], 1)
        self.assertEqual(summary["empty"]["avg_er"], 0.0)


class TestWriteReports(unittest.TestCase):
    def test_writes_markdown_and_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md = Path(tmpdir) / "report.md"
            js = Path(tmpdir) / "report.json"
            with mock.patch.object(analyze_engagement, "REPORT_MD", md), \
                 mock.patch.object(analyze_engagement, "REPORT_JSON", js):
                summary = analyze_engagement.summarize([_post("", er=3.5, views=10)])
                analyze_engagement.write_reports(summary, total_posts=1)

            self.assertTrue(md.exists())
            self.assertTrue(js.exists())
            content = md.read_text()
            self.assertIn("| Category |", content)
            self.assertIn("empty", content)
            data = json.loads(js.read_text())
            self.assertEqual(data["posts_analyzed"], 1)
            self.assertEqual(data["categories"]["empty"]["avg_er"], 3.5)


class TestFetchAnalytics(unittest.TestCase):
    def test_success(self):
        proc = mock.Mock(returncode=0, stdout=json.dumps({"posts": [{"_id": "p1"}]}), stderr="")
        with mock.patch.object(analyze_engagement, "ZERNIO", "/bin/zernio"), \
             mock.patch.object(analyze_engagement.subprocess, "run", return_value=proc):
            self.assertEqual(analyze_engagement.fetch_analytics(), [{"_id": "p1"}])

    def test_missing_zernio_raises(self):
        with mock.patch.object(analyze_engagement, "ZERNIO", ""), self.assertRaises(RuntimeError):
            analyze_engagement.fetch_analytics()

    def test_nonzero_exit_raises(self):
        proc = mock.Mock(returncode=1, stdout="", stderr="rate limited")
        with mock.patch.object(analyze_engagement, "ZERNIO", "/bin/zernio"), \
             mock.patch.object(analyze_engagement.subprocess, "run", return_value=proc), \
             self.assertRaises(RuntimeError):
            analyze_engagement.fetch_analytics()


class TestMain(unittest.TestCase):
    def test_missing_zernio_returns_2(self):
        with mock.patch.object(analyze_engagement, "ZERNIO", ""):
            buf = io.StringIO()
            with mock.patch("sys.argv", ["analyze_engagement.py"]), redirect_stdout(buf):
                code = analyze_engagement.main()
        self.assertEqual(code, 2)
        self.assertIn("zernio CLI not found", buf.getvalue())

    def test_no_posts_returns_0(self):
        with mock.patch.object(analyze_engagement, "fetch_analytics", return_value=[]):
            buf = io.StringIO()
            with mock.patch("sys.argv", ["analyze_engagement.py"]), redirect_stdout(buf):
                code = analyze_engagement.main()
        self.assertEqual(code, 0)
        self.assertIn("No posts", buf.getvalue())

    def test_happy_path_writes_reports(self):
        posts = [_post(CTA_CAPTIONS[0], er=2.5, views=500)]
        with tempfile.TemporaryDirectory() as tmpdir, \
             mock.patch.object(analyze_engagement, "fetch_analytics", return_value=posts), \
             mock.patch.object(analyze_engagement, "REPORT_MD", Path(tmpdir) / "r.md"), \
             mock.patch.object(analyze_engagement, "REPORT_JSON", Path(tmpdir) / "r.json"):
            buf = io.StringIO()
            with mock.patch("sys.argv", ["analyze_engagement.py"]), redirect_stdout(buf):
                code = analyze_engagement.main()
        self.assertEqual(code, 0)
        self.assertIn("Analyzed 1 posts", buf.getvalue())

    def test_cli_error_returns_2(self):
        with mock.patch.object(
            analyze_engagement, "fetch_analytics", side_effect=RuntimeError("boom")
        ):
            buf = io.StringIO()
            with mock.patch("sys.argv", ["analyze_engagement.py"]), redirect_stdout(buf):
                code = analyze_engagement.main()
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
