"""
Unit tests for scripts/post_utils.py's create_post function:
  - draft mode, scheduled mode
  - command construction (flags, accounts, tags)
  - success, rate-limit retry, max-retry exhaustion
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.post_utils import ACCOUNT_ID, create_post

SAMPLE_URL = "https://player.vimeo.com/external/video-files/12345/hd.mp4"
SAMPLE_CAPTION = "Test caption with hashtags #drone #viral"
SAMPLE_TIME = "2026-06-01T10:00:00-04:00"


# ---------------------------------------------------------------------------
# Command construction (verify what gets passed to subprocess.run)
# ---------------------------------------------------------------------------
class TestCommandConstruction(unittest.TestCase):
    def setUp(self):
        patcher_zernio = mock.patch("scripts.post_utils.ZERNI0", "zernio")
        patcher_zernio.start()
        self.addCleanup(patcher_zernio.stop)
        self.patcher = mock.patch("scripts.post_utils.subprocess.run", return_value=mock.Mock(returncode=0))
        self.mock_run = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _call_args(self):
        """Return the list-form command passed to subprocess.run."""
        self.mock_run.assert_called_once()
        return self.mock_run.call_args[0][0]

    def test_draft_mode_includes_draft_flag(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        cmd = self._call_args()
        self.assertIn("--draft", cmd)
        self.assertNotIn("--scheduledAt", cmd)

    def test_scheduled_mode_includes_scheduled_at(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, SAMPLE_TIME)
        cmd = self._call_args()
        self.assertIn("--scheduledAt", cmd)
        self.assertIn(SAMPLE_TIME, cmd)
        self.assertNotIn("--draft", cmd)

    def test_tags_hashtags_timezone_always_present_for_ig(self):
        # Default is IG
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        cmd = self._call_args()
        self.assertIn("--tags", cmd)
        self.assertIn("--hashtags", cmd)
        self.assertIn("--timezone", cmd)

    def test_default_accounts_uses_account_id(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        cmd = self._call_args()
        self.assertIn(ACCOUNT_ID, cmd)

    def test_custom_accounts_overrides_default(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, accounts="6a0afc8a5e333c0529912a50")
        cmd = self._call_args()
        self.assertIn("6a0afc8a5e333c0529912a50", cmd)

    def test_media_and_text_included(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        cmd = self._call_args()
        idx_url = cmd.index("--media")
        self.assertEqual(cmd[idx_url + 1], SAMPLE_URL)
        idx_text = cmd.index("--text")
        self.assertEqual(cmd[idx_text + 1], SAMPLE_CAPTION)


# ---------------------------------------------------------------------------
# Success / failure paths
# ---------------------------------------------------------------------------
class TestSuccessPath(unittest.TestCase):
    def setUp(self):
        patcher_zernio = mock.patch("scripts.post_utils.ZERNI0", "zernio")
        patcher_zernio.start()
        self.addCleanup(patcher_zernio.stop)

    def test_returns_true_on_success(self):
        with mock.patch("scripts.post_utils.subprocess.run", return_value=mock.Mock(returncode=0)):
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        self.assertTrue(result)

    def test_returns_false_after_max_retries(self):
        fail_result = mock.Mock(returncode=1, stdout="generic error", stderr="")
        with mock.patch("scripts.post_utils.subprocess.run", return_value=fail_result):
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, max_retries=2)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Rate-limit / Server Error retry
# ---------------------------------------------------------------------------
class TestRetryLogic(unittest.TestCase):
    def setUp(self):
        patcher_zernio = mock.patch("scripts.post_utils.ZERNI0", "zernio")
        patcher_zernio.start()
        self.addCleanup(patcher_zernio.stop)

    def test_retries_on_429(self):
        rate_limited = mock.Mock(returncode=1, stdout="", stderr="HTTP 429 Too Many Requests")
        success = mock.Mock(returncode=0)
        with mock.patch("scripts.post_utils.subprocess.run", side_effect=[rate_limited, success]) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            # wait_time = 60 * 1
            m_sleep.assert_called_once_with(60)

    def test_retries_on_500(self):
        server_error = mock.Mock(returncode=1, stdout="500 Internal Server Error", stderr="")
        success = mock.Mock(returncode=0)
        with mock.patch("scripts.post_utils.subprocess.run", side_effect=[server_error, success]) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            # wait_time = 10 * 1
            m_sleep.assert_called_once_with(10)

    def test_stops_on_generic_error(self):
        fail = mock.Mock(returncode=1, stdout="something broke", stderr="")
        with mock.patch("scripts.post_utils.subprocess.run", return_value=fail) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
            self.assertFalse(result)
            self.assertEqual(m_run.call_count, 1)
            m_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
