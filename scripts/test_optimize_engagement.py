"""
Unit tests for scripts/optimize_engagement.py
"""

import sys
import unittest
import json
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.optimize_engagement import classify_caption, calculate_weights, main


class TestClassifyCaption(unittest.TestCase):
    def test_classify_empty(self):
        self.assertEqual(classify_caption(""), "empty")
        self.assertEqual(classify_caption("   "), "empty")
        self.assertEqual(classify_caption("#drone #viral"), "empty")
        self.assertEqual(classify_caption("  #drone  #viral  "), "empty")

    def test_classify_value(self):
        self.assertEqual(classify_caption("Here is a quick tip for flying #drone"), "value")
        self.assertEqual(classify_caption("workflow to export 4K"), "value")
        self.assertEqual(classify_caption("always use ND filters"), "value")

    def test_classify_cta(self):
        self.assertEqual(classify_caption("What is your favorite spot? 👇"), "cta")
        self.assertEqual(classify_caption("Rate this 1-10"), "cta")
        self.assertEqual(classify_caption("DM us for info"), "cta")

    def test_classify_micro(self):
        self.assertEqual(classify_caption("Smooth drone flight through the mountains"), "micro")
        self.assertEqual(classify_caption("Living in a dream"), "micro")


class TestCalculateWeights(unittest.TestCase):
    def test_calculate_weights_empty_categories(self):
        categories = {
            "empty": [],
            "micro": [],
            "value": [],
            "cta": []
        }
        weights = calculate_weights(categories)
        self.assertEqual(weights["empty"], 0.30)
        self.assertEqual(weights["micro"], 0.22)
        self.assertEqual(weights["value"], 0.18)
        self.assertEqual(weights["cta"], 0.30)

    def test_calculate_weights_proportional_distribution(self):
        # 10% floor for each. Remaining 60% distributed proportionally
        # Average ER: empty: 1.0, micro: 2.0, value: 3.0, cta: 4.0
        # Total ER = 10.0
        # empty = 0.10 + (1/10)*0.60 = 0.16
        # micro = 0.10 + (2/10)*0.60 = 0.22
        # value = 0.10 + (3/10)*0.60 = 0.28
        # cta = 0.10 + (4/10)*0.60 = 0.34
        categories = {
            "empty": [1.0],
            "micro": [2.0],
            "value": [3.0],
            "cta": [4.0]
        }
        weights = calculate_weights(categories)
        self.assertAlmostEqual(weights["empty"], 0.16)
        self.assertAlmostEqual(weights["micro"], 0.22)
        self.assertAlmostEqual(weights["value"], 0.28)
        self.assertAlmostEqual(weights["cta"], 0.34)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_calculate_weights_ensures_exact_sum(self):
        # Verify that even with weird values that round to sums != 1.0, the adjust step fixes it
        categories = {
            "empty": [0.12345],
            "micro": [0.54321],
            "value": [0.98765],
            "cta": [0.24680]
        }
        weights = calculate_weights(categories)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)


class TestMainOptimization(unittest.TestCase):
    @mock.patch("scripts.optimize_engagement.subprocess.run")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("os.makedirs")
    def test_main_runs_correctly(self, mock_makedirs, mock_open, mock_run):
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout=json.dumps({
                "posts": [
                    {"content": "workflow tip", "analytics": {"engagementRate": 2.0}},
                    {"content": "rate 1-10 👇", "analytics": {"engagementRate": 4.0}},
                    {"content": "just a reel", "analytics": {"engagementRate": 1.0}},
                    {"content": "#drone #viral", "analytics": {"engagementRate": 3.0}}
                ]
            }),
            stderr=""
        )
        
        main()
        
        # Verify file was written
        mock_open.assert_called_with("/Users/cmd/galaxycoilszernio/logs/engagement_weights.json", "w")


if __name__ == "__main__":
    unittest.main()
