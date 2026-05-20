"""
Unit tests for scripts/secure_dedup.py core functions:
  - load_history()
  - extract_id(url)
  - record_scheduled(video_id)
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Ensure the project root is on sys.path so we can import from scripts.secure_dedup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.secure_dedup import extract_id, load_history, record_scheduled


# ---------------------------------------------------------------------------
# extract_id
# ---------------------------------------------------------------------------
class TestExtractId(unittest.TestCase):
    def test_valid_url_returns_id(self):
        url = "https://player.vimeo.com/external/123/video-files/987654321/hd.mp4"
        self.assertEqual(extract_id(url), "987654321")

    def test_url_with_multiple_digit_groups_returns_video_files_id(self):
        url = "https://cdn.pexels.com/video-files/112233/another.mov"
        self.assertEqual(extract_id(url), "112233")

    def test_none_returns_none(self):
        self.assertIsNone(extract_id(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(extract_id(""))

    def test_no_video_files_returns_none(self):
        self.assertIsNone(extract_id("https://example.com/photos/12345/image.jpg"))

    def test_video_files_without_number_returns_none(self):
        self.assertIsNone(extract_id("https://example.com/video-files/file.mp4"))

    def test_real_pexels_url_format(self):
        """Matches the format actually returned by the Pexels API."""
        url = "https://player.vimeo.com/external/123456789.sd.mp4?s=abc&profile_id=123"
        self.assertIsNone(extract_id(url))


# ---------------------------------------------------------------------------
# load_history
# ---------------------------------------------------------------------------
class TestLoadHistory(unittest.TestCase):
    def test_no_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = os.path.join(tmpdir, "nonexistent.log")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", nonexistent):
                self.assertEqual(load_history(), set())

    def test_empty_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.log")
            open(path, "w").close()
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", path):
                self.assertEqual(load_history(), set())

    def test_single_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "single.log")
            with open(path, "w") as f:
                f.write("12345\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", path):
                self.assertEqual(load_history(), {"12345"})

    def test_multiple_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "multi.log")
            with open(path, "w") as f:
                f.write("111\n222\n333\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", path):
                self.assertEqual(load_history(), {"111", "222", "333"})

    def test_blank_lines_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "blanks.log")
            with open(path, "w") as f:
                f.write("111\n\n222\n   \n333\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", path):
                self.assertEqual(load_history(), {"111", "222", "333"})

    def test_trailing_newline_handled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "trailing.log")
            with open(path, "w") as f:
                f.write("abc\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", path):
                self.assertEqual(load_history(), {"abc"})


# ---------------------------------------------------------------------------
# record_scheduled
# ---------------------------------------------------------------------------
class TestRecordScheduled(unittest.TestCase):
    def test_new_id_appended(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist = os.path.join(tmpdir, "history.log")
            with open(hist, "w") as f:
                f.write("existing1\nexisting2\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", hist):
                record_scheduled("new_one")
                with open(hist) as f:
                    lines = f.read().splitlines()
                self.assertIn("new_one", lines)
                # existing IDs still there
                self.assertIn("existing1", lines)
                self.assertIn("existing2", lines)

    def test_duplicate_id_not_appended(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist = os.path.join(tmpdir, "history.log")
            with open(hist, "w") as f:
                f.write("dup\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", hist):
                record_scheduled("dup")
                with open(hist) as f:
                    lines = [l for l in f.read().splitlines() if l]
                self.assertEqual(lines, ["dup"])

    def test_empty_id_does_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist = os.path.join(tmpdir, "history.log")
            with open(hist, "w") as f:
                f.write("before\n")
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", hist):
                record_scheduled("")
                with open(hist) as f:
                    lines = [l for l in f.read().splitlines() if l]
                self.assertEqual(lines, ["before"])

    def test_none_id_does_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist = os.path.join(tmpdir, "history.log")
            open(hist, "w").close()  # empty file
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", hist):
                record_scheduled(None)
                with open(hist) as f:
                    self.assertEqual(f.read(), "")

    def test_file_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist = os.path.join(tmpdir, "brand_new.log")
            self.assertFalse(os.path.exists(hist))
            with mock.patch("scripts.secure_dedup.HISTORY_FILE", hist):
                record_scheduled("first_ever")
                self.assertTrue(os.path.exists(hist))
                with open(hist) as f:
                    lines = [l for l in f.read().splitlines() if l]
                self.assertEqual(lines, ["first_ever"])


if __name__ == "__main__":
    unittest.main()
