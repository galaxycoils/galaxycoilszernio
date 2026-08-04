"""
Unit tests for scripts/update_empty_posts.py:
  - select_posts_to_fix(): the ratio-aware guard that protects the
    intentional ~30% empty-caption mix (engagement pivot)
  - find_empty_posts(), get_post_details(), fix_post(), main() paths
"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import update_empty_posts as uep
from scripts.update_empty_posts import select_posts_to_fix


class TestSelectPostsToFix(unittest.TestCase):
    def test_intentional_mix_is_left_alone(self):
        """15 empties in a 50-post queue (30%) is the DESIGNED mix — the old
        --min-empty 3 behavior would have 'fixed' (destroyed) all 15."""
        empties = [f"p{i}" for i in range(15)]
        self.assertEqual(select_posts_to_fix(empties, total_scheduled=50), [])

    def test_excess_empties_fixed_down_to_target(self):
        """25 empties in 50 (50%) exceeds max ratio 35% → fix down to 30% = 15,
        so exactly 10 posts get fixed."""
        empties = [f"p{i}" for i in range(25)]
        result = select_posts_to_fix(empties, total_scheduled=50)
        self.assertEqual(len(result), 10)
        self.assertEqual(result, empties[:10])

    def test_ratio_exactly_at_max_is_left_alone(self):
        empties = [f"p{i}" for i in range(7)]  # 7/20 = 35%
        self.assertEqual(select_posts_to_fix(empties, total_scheduled=20), [])

    def test_min_empty_floor_respected(self):
        empties = ["a", "b", "c"]
        self.assertEqual(
            select_posts_to_fix(empties, total_scheduled=5, min_empty=3), []
        )

    def test_no_scheduled_posts_no_fix(self):
        self.assertEqual(select_posts_to_fix(["a"], total_scheduled=0), [])

    def test_empty_queue_no_fix(self):
        self.assertEqual(select_posts_to_fix([], total_scheduled=50), [])

    def test_small_queue_uses_ratio(self):
        """4 empties in 10 (40%) > 35% → fix 1 (down to 30% = 3)."""
        result = select_posts_to_fix(["a", "b", "c", "d"], total_scheduled=10)
        self.assertEqual(result, ["a"])

    def test_custom_ratios(self):
        empties = [f"p{i}" for i in range(10)]  # 10/20 = 50%
        result = select_posts_to_fix(
            empties, total_scheduled=20, max_empty_ratio=0.40, target_ratio=0.20
        )
        self.assertEqual(len(result), 6)  # down to int(20*0.20)=4

    def test_returns_list_type(self):
        result = select_posts_to_fix([f"p{i}" for i in range(25)], 50)
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# find_empty_posts
# ---------------------------------------------------------------------------
class TestFindEmptyPosts(unittest.TestCase):
    def test_returns_ids_and_total(self):
        data = {"posts": [
            {"_id": "a", "content": ""},
            {"_id": "b", "content": "hello"},
            {"_id": "c", "content": "   "},
            {"_id": "d"},  # missing content key
        ]}
        with mock.patch.object(uep, "_run_json", return_value=data):
            ids, total = uep.find_empty_posts()
        self.assertEqual(ids, ["a", "c", "d"])
        self.assertEqual(total, 4)

    def test_cli_failure_returns_empty(self):
        with mock.patch.object(uep, "_run_json", return_value=None):
            ids, total = uep.find_empty_posts()
        self.assertEqual((ids, total), ([], 0))


# ---------------------------------------------------------------------------
# get_post_details
# ---------------------------------------------------------------------------
class TestGetPostDetails(unittest.TestCase):
    def test_post_root_object(self):
        """zernio posts:get wraps the post in a 'post' key (MEMORY.md quirk)."""
        data = {"post": {
            "mediaItems": [{"url": "https://x/video-files/1/hd.mp4"}],
            "scheduledFor": "2026-06-01T10:00:00.000Z",
            "accountIds": ["acc1"],
        }}
        with mock.patch.object(uep, "_run_json", return_value=data):
            details = uep.get_post_details("pid")
        self.assertEqual(details["media_url"], "https://x/video-files/1/hd.mp4")
        self.assertEqual(details["scheduled_for"], "2026-06-01T10:00:00.000Z")
        self.assertEqual(details["account_ids"], ["acc1"])

    def test_bare_post_object(self):
        data = {"_id": "pid", "mediaItems": [], "scheduledFor": ""}
        with mock.patch.object(uep, "_run_json", return_value=data):
            details = uep.get_post_details("pid")
        self.assertEqual(details["media_url"], "")

    def test_cli_failure_returns_none(self):
        with mock.patch.object(uep, "_run_json", return_value=None):
            self.assertIsNone(uep.get_post_details("pid"))


# ---------------------------------------------------------------------------
# fix_post
# ---------------------------------------------------------------------------
GOOD_DETAILS = {
    "media_url": "https://x/video-files/1/hd.mp4",
    "scheduled_for": "2026-06-01T10:00:00.000Z",
    "account_ids": ["acc1", "acc2"],
}


class TestFixPost(unittest.TestCase):
    def _run(self, details=GOOD_DETAILS, delete_ok=True, create_ok=True):
        with mock.patch.object(uep, "get_post_details", return_value=details), \
             mock.patch.object(uep, "_run_ok", return_value=delete_ok), \
             mock.patch.object(uep, "_create_post", return_value=create_ok) as create, \
             mock.patch.object(uep.time, "sleep"), \
             redirect_stdout(io.StringIO()):
            result = uep.fix_post("pid")
        return result, create

    def test_success_recreates_with_same_slot_and_accounts(self):
        result, create = self._run()
        self.assertTrue(result)
        args, kwargs = create.call_args
        self.assertEqual(args[0], GOOD_DETAILS["media_url"])
        self.assertEqual(args[2], GOOD_DETAILS["scheduled_for"])
        self.assertEqual(kwargs["accounts"], "acc1,acc2")

    def test_no_details_skips(self):
        result, create = self._run(details=None)
        self.assertFalse(result)
        create.assert_not_called()

    def test_no_media_skips(self):
        result, create = self._run(details={**GOOD_DETAILS, "media_url": ""})
        self.assertFalse(result)
        create.assert_not_called()

    def test_no_schedule_skips(self):
        result, create = self._run(details={**GOOD_DETAILS, "scheduled_for": ""})
        self.assertFalse(result)
        create.assert_not_called()

    def test_delete_failure_skips(self):
        result, create = self._run(delete_ok=False)
        self.assertFalse(result)
        create.assert_not_called()

    def test_create_failure_returns_false(self):
        result, _ = self._run(create_ok=False)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
class TestMain(unittest.TestCase):
    def _run_main(self, empty_ids, total, argv=None):
        with mock.patch.object(uep, "find_empty_posts", return_value=(empty_ids, total)), \
             mock.patch.object(uep, "fix_post", return_value=True) as fix, \
             mock.patch.object(uep, "dry_run") as dry, \
             mock.patch.object(uep.time, "sleep"), \
             mock.patch("sys.argv", ["update_empty_posts.py"] + (argv or [])):
            buf = io.StringIO()
            with redirect_stdout(buf):
                uep.main()
        return buf.getvalue(), fix, dry

    def test_no_empties(self):
        out, fix, dry = self._run_main([], 50)
        self.assertIn("No empty-caption posts found", out)
        fix.assert_not_called()
        dry.assert_not_called()

    def test_intentional_mix_skipped(self):
        """15/50 empties (30%) — the designed mix must NOT be 'fixed'."""
        out, fix, dry = self._run_main([f"p{i}" for i in range(15)], 50)
        self.assertIn("within the intentional mix", out)
        fix.assert_not_called()
        dry.assert_not_called()

    def test_excess_fixed(self):
        """25/50 empties (50%) → fix 10."""
        out, fix, dry = self._run_main([f"p{i}" for i in range(25)], 50)
        self.assertIn("fixing 10", out)
        self.assertEqual(fix.call_count, 10)
        dry.assert_not_called()

    def test_dry_run_delegates_selected_ids(self):
        out, fix, dry = self._run_main([f"p{i}" for i in range(25)], 50, argv=["--dry-run"])
        self.assertEqual(fix.call_count, 0)
        self.assertEqual(len(dry.call_args[0][0]), 10)

    def test_min_empty_floor(self):
        out, fix, dry = self._run_main(["a", "b"], 3, argv=["--min-empty", "3"])
        fix.assert_not_called()


# ---------------------------------------------------------------------------
# _run_json / _run_ok / dry_run
# ---------------------------------------------------------------------------
class TestSubprocessWrappers(unittest.TestCase):
    def test_run_json_success(self):
        proc = mock.Mock(returncode=0, stdout='{"ok": true}', stderr="")
        with mock.patch.object(uep.subprocess, "run", return_value=proc):
            self.assertEqual(uep._run_json(["zernio"]), {"ok": True})

    def test_run_json_cli_error_returns_none(self):
        proc = mock.Mock(returncode=1, stdout="", stderr="boom")
        with mock.patch.object(uep.subprocess, "run", return_value=proc), \
             redirect_stdout(io.StringIO()):
            self.assertIsNone(uep._run_json(["zernio"]))

    def test_run_json_invalid_json_returns_none(self):
        proc = mock.Mock(returncode=0, stdout="not json", stderr="")
        with mock.patch.object(uep.subprocess, "run", return_value=proc), \
             redirect_stdout(io.StringIO()):
            self.assertIsNone(uep._run_json(["zernio"]))

    def test_run_ok(self):
        with mock.patch.object(uep.subprocess, "run",
                               return_value=mock.Mock(returncode=0)):
            self.assertTrue(uep._run_ok(["zernio"]))
        with mock.patch.object(uep.subprocess, "run",
                               return_value=mock.Mock(returncode=1)):
            self.assertFalse(uep._run_ok(["zernio"]))


class TestDryRun(unittest.TestCase):
    def test_dry_run_reports_each_post(self):
        with mock.patch.object(uep, "get_post_details", return_value=GOOD_DETAILS), \
             mock.patch.object(uep.time, "sleep"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                uep.dry_run(["p1", "p2"])
        out = buf.getvalue()
        self.assertIn("DRY RUN: 2 empty-caption post(s)", out)
        self.assertIn("no posts were modified", out)

    def test_dry_run_skips_undetails_and_no_media(self):
        with mock.patch.object(uep, "get_post_details",
                               side_effect=[None, {**GOOD_DETAILS, "media_url": ""}]), \
             mock.patch.object(uep.time, "sleep"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                uep.dry_run(["p1", "p2"])
        out = buf.getvalue()
        self.assertIn("SKIP (could not fetch)", out)
        self.assertIn("SKIP (no media)", out)


if __name__ == "__main__":
    unittest.main()
