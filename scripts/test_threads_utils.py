"""Unit tests for scripts/threads_utils.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.threads_utils import build_threads_caption, enrich_for_threads, strip_ig_seo_block


class TestStripIgSeoBlock(unittest.TestCase):
    def test_removes_trailing_hashtag_block(self):
        raw = "Which shot wins?\n\n#GalaxyCoils #Drone #Fpv"
        self.assertEqual(strip_ig_seo_block(raw), "Which shot wins?")


class TestBuildThreadsCaption(unittest.TestCase):
    def test_strips_ig_hashtag_block_via_enrich(self):
        ig_style = "Which shot wins?\n\n#GalaxyCoils #Drone #Fpv"
        result = build_threads_caption(ig_style.split("\n\n")[0])
        self.assertNotIn("#GalaxyCoils", result)
        self.assertLessEqual(len(result), 500)

    def test_empty_base_uses_fallback(self):
        result = build_threads_caption("")
        self.assertTrue(len(result) >= 20)

    def test_enrich_respects_500_char_limit(self):
        long_core = " ".join(["aerial"] * 80)
        result = enrich_for_threads(long_core)
        self.assertLessEqual(len(result), 500)


if __name__ == "__main__":
    unittest.main()
