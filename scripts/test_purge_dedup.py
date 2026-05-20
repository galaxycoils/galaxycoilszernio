"""
Unit tests for purge_zernio_duplicates.py's dedup logic:
  - oldest-first ordering keeps the first occurrence
  - duplicates within scheduled queue detected
  - duplicates against history.log detected
  - posts without media/extractable ID skipped
  - dry-run prevents deletes and writes
  - mixed scenarios
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import purge_zernio_duplicates


# ---------------------------------------------------------------------------
# Post factories
# ---------------------------------------------------------------------------
def _make_post(_id, created_at, scheduled_for, pexels_id):
    """Factory for a scheduled post dict matching the zernio API shape."""
    return {
        "_id": _id,
        "createdAt": created_at,
        "scheduledFor": scheduled_for,
        "mediaItems": [{"url": f"https://cdn.pexels.com/video-files/{pexels_id}/hd.mp4"}],
    }


def _make_post_no_media(_id, created_at, scheduled_for):
    """Post with no mediaItems field."""
    return {
        "_id": _id,
        "createdAt": created_at,
        "scheduledFor": scheduled_for,
    }


def _make_post_no_id(_id, created_at, scheduled_for):
    """Post with media but no extractable Pexels ID."""
    return {
        "_id": _id,
        "createdAt": created_at,
        "scheduledFor": scheduled_for,
        "mediaItems": [{"url": "https://example.com/not-a-video-file/image.jpg"}],
    }


# ---------------------------------------------------------------------------
# Shared helper — mocks all deps of main() and captures side effects
# ---------------------------------------------------------------------------
def _run_purge(history_ids, scheduled_posts, dry_run=False):
    """Run main() with all external deps mocked.

    Returns (deleted_ids: list, new_ids_recorded: list) so callers can
    assert on what the dedup logic decided.

    NOTE: patch targets are ``purge_zernio_duplicates.<name>`` (not
    ``scripts.secure_dedup.<name>``) because the source file uses
    ``from scripts.secure_dedup import ...`` — the imported names are
    local bindings in the ``purge_zernio_duplicates`` module.
    """
    history_set = set(history_ids)
    deleted = []
    recorded = []

    def fake_load_history():
        return history_set.copy()

    def fake_fetch_posts(status):
        if status == "scheduled":
            return scheduled_posts
        return []

    def fake_record_scheduled(pexels_id):
        recorded.append(pexels_id)
        history_set.add(pexels_id)

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "posts:delete":
            deleted.append(cmd[2])
        return mock.Mock(returncode=0)

    with mock.patch("purge_zernio_duplicates.load_history", fake_load_history), \
         mock.patch("purge_zernio_duplicates.fetch_posts", fake_fetch_posts), \
         mock.patch("purge_zernio_duplicates.record_scheduled", fake_record_scheduled), \
         mock.patch("purge_zernio_duplicates.subprocess.run", fake_subprocess_run), \
         mock.patch("argparse.ArgumentParser.parse_args",
                    return_value=mock.Mock(dry_run=dry_run)):
        purge_zernio_duplicates.main()

    return deleted, recorded


# ---------------------------------------------------------------------------
# No posts
# ---------------------------------------------------------------------------
class TestNoPosts(unittest.TestCase):
    def test_no_scheduled_posts(self):
        deleted, recorded = _run_purge([], [], dry_run=False)
        self.assertEqual(deleted, [])
        self.assertEqual(recorded, [])


# ---------------------------------------------------------------------------
# All unique  (no duplicates anywhere)
# ---------------------------------------------------------------------------
class TestAllUnique(unittest.TestCase):
    def test_all_unique(self):
        history = ["100"]
        posts = [
            _make_post("a", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z", "200"),
            _make_post("b", "2026-06-01T11:00:00Z", "2026-06-01T11:00:00Z", "300"),
        ]
        deleted, recorded = _run_purge(history, posts, dry_run=False)

        self.assertEqual(deleted, [])
        # Both unique scheduled IDs should be recorded
        self.assertEqual(set(recorded), {"200", "300"})


# ---------------------------------------------------------------------------
# Duplicate within scheduled queue (oldest kept)
# ---------------------------------------------------------------------------
class TestIntraQueueDuplicates(unittest.TestCase):
    def test_oldest_kept(self):
        """Two posts with the same Pexels ID — oldest (by createdAt) kept."""
        posts = [
            _make_post("older", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z", "555"),
            _make_post("newer", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "555"),
        ]
        deleted, recorded = _run_purge([], posts, dry_run=False)

        self.assertEqual(deleted, ["newer"])
        self.assertEqual(recorded, ["555"])

    def test_middle_duplicate(self):
        """Three posts; first and last share an ID — only first kept."""
        posts = [
            _make_post("1", "2026-06-01T09:00:00Z", "2026-06-01T09:00:00Z", "111"),
            _make_post("2", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z", "222"),
            _make_post("3", "2026-06-01T11:00:00Z", "2026-06-01T11:00:00Z", "111"),
        ]
        deleted, recorded = _run_purge([], posts, dry_run=False)

        self.assertEqual(deleted, ["3"])
        self.assertEqual(set(recorded), {"111", "222"})


# ---------------------------------------------------------------------------
# Duplicate against history
# ---------------------------------------------------------------------------
class TestHistoryDuplicates(unittest.TestCase):
    def test_scheduled_matches_history(self):
        """A scheduled post whose Pexels ID is already in history → deleted."""
        history = ["999"]
        posts = [
            _make_post("dup", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z", "999"),
            _make_post("uniq", "2026-06-01T11:00:00Z", "2026-06-01T11:00:00Z", "888"),
        ]
        deleted, recorded = _run_purge(history, posts, dry_run=False)

        self.assertEqual(deleted, ["dup"])
        self.assertEqual(recorded, ["888"])


# ---------------------------------------------------------------------------
# Posts without extractable Pexels ID
# ---------------------------------------------------------------------------
class TestUnidentifiablePosts(unittest.TestCase):
    def test_no_media_items_skipped(self):
        posts = [
            _make_post_no_media("no_media", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z"),
            _make_post("good", "2026-06-01T11:00:00Z", "2026-06-01T11:00:00Z", "777"),
        ]
        deleted, recorded = _run_purge([], posts, dry_run=False)

        self.assertEqual(deleted, [])
        self.assertEqual(recorded, ["777"])

    def test_no_extractable_id_skipped(self):
        posts = [
            _make_post_no_id("no_id", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z"),
            _make_post("good", "2026-06-01T11:00:00Z", "2026-06-01T11:00:00Z", "666"),
        ]
        deleted, recorded = _run_purge([], posts, dry_run=False)

        self.assertEqual(deleted, [])
        self.assertEqual(recorded, ["666"])


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------
class TestDryRun(unittest.TestCase):
    def test_dry_run_no_deletes_and_no_records(self):
        """In dry-run mode, nothing is deleted and nothing written to history."""
        history = ["111"]
        posts = [
            _make_post("dup", "2026-06-01T10:00:00Z", "2026-06-01T10:00:00Z", "111"),
            _make_post("uniq", "2026-06-01T11:00:00Z", "2026-06-01T11:00:00Z", "222"),
        ]
        deleted, recorded = _run_purge(history, posts, dry_run=True)

        self.assertEqual(deleted, [])
        self.assertEqual(recorded, [])


# ---------------------------------------------------------------------------
# Sorting: oldest-first ordering
# ---------------------------------------------------------------------------
class TestOldestFirstOrdering(unittest.TestCase):
    def test_unsorted_input_is_sorted_before_dedup(self):
        """Posts arrive unsorted; oldest-by-createdAt is kept."""
        posts = [
            _make_post("newest", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "444"),
            _make_post("oldest", "2026-06-01T09:00:00Z", "2026-06-01T09:00:00Z", "444"),
            _make_post("middle", "2026-06-01T10:30:00Z", "2026-06-01T10:30:00Z", "444"),
        ]
        deleted, recorded = _run_purge([], posts, dry_run=False)

        # "oldest" kept; "middle" and "newest" deleted
        self.assertEqual(set(deleted), {"middle", "newest"})
        self.assertEqual(recorded, ["444"])

    def test_different_ids_not_confused(self):
        """Sorted posts with distinct IDs — all unique.  (IDs must be numeric
        because extract_id uses \\d+ regex.)"""
        posts = [
            _make_post("b", "2026-06-01T12:00:00Z", "2026-06-01T12:00:00Z", "333"),
            _make_post("a", "2026-06-01T09:00:00Z", "2026-06-01T09:00:00Z", "111"),
            _make_post("c", "2026-06-01T10:30:00Z", "2026-06-01T10:30:00Z", "222"),
        ]
        deleted, recorded = _run_purge([], posts, dry_run=False)

        self.assertEqual(deleted, [])
        self.assertEqual(set(recorded), {"111", "222", "333"})


if __name__ == "__main__":
    unittest.main()
