"""
Unit tests for scripts/captions_pool.py:
  - classify_caption(): pool membership, heuristics, edge cases
  - pool integrity: every pool caption classifies into its own category
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.captions_pool import (
    CATEGORIES,
    CTA_CAPTIONS,
    MICRO_HOOKS,
    VALUE_CAPTIONS,
    classify_caption,
)


class TestPoolIntegrity(unittest.TestCase):
    """The classifier must agree with generate_caption_plan()'s pools."""

    def test_all_cta_captions_classify_as_cta(self):
        for caption in CTA_CAPTIONS:
            self.assertEqual(classify_caption(caption), "cta", caption)

    def test_all_micro_hooks_classify_as_micro_hook(self):
        for caption in MICRO_HOOKS:
            self.assertEqual(classify_caption(caption), "micro-hook", caption)

    def test_all_value_captions_classify_as_value(self):
        for caption in VALUE_CAPTIONS:
            self.assertEqual(classify_caption(caption), "value", caption)

    def test_pools_have_no_duplicates(self):
        for pool in (CTA_CAPTIONS, MICRO_HOOKS, VALUE_CAPTIONS):
            self.assertEqual(len(pool), len(set(pool)))

    def test_pools_do_not_overlap(self):
        self.assertFalse(set(CTA_CAPTIONS) & set(MICRO_HOOKS))
        self.assertFalse(set(CTA_CAPTIONS) & set(VALUE_CAPTIONS))
        self.assertFalse(set(MICRO_HOOKS) & set(VALUE_CAPTIONS))


class TestClassifyEdgeCases(unittest.TestCase):
    def test_empty(self):
        for content in ("", "   ", None):
            self.assertEqual(classify_caption(content), "empty")

    def test_hashtag_only(self):
        self.assertEqual(classify_caption("#drone #fpv #cinematic"), "hashtag-only")

    def test_day_template_legacy(self):
        self.assertEqual(classify_caption("Day 12 delivery: drone shots"), "day-template")

    def test_unknown_value_heuristic(self):
        self.assertEqual(classify_caption("Save this workflow for later"), "value")

    def test_unknown_cta_heuristic(self):
        self.assertEqual(classify_caption("Which one would you pick for your next trip?"), "cta")

    def test_unknown_short_statement_is_micro_hook(self):
        self.assertEqual(classify_caption("Pure flow state"), "micro-hook")

    def test_unknown_long_statement_is_other(self):
        self.assertEqual(
            classify_caption("This is a longer reflective caption about flying drones over mountains at dusk"),
            "other",
        )

    def test_categories_stable(self):
        """Report schemas depend on this exact tuple."""
        self.assertEqual(
            CATEGORIES,
            ("empty", "cta", "micro-hook", "value", "hashtag-only", "day-template", "other"),
        )


if __name__ == "__main__":
    unittest.main()
