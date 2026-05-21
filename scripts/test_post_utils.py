"""
Unit tests for scripts/post_utils.py's create_post function:
  - draft mode, scheduled mode, ValueError guard
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
SAMPLE_CAPTION = "Test caption"
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

    def test_tags_hashtags_timezone_always_present(self):
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
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, accounts="custom_id")
        cmd = self._call_args()
        self.assertIn("custom_id", cmd)
        self.assertNotIn(ACCOUNT_ID, cmd)

    def test_media_and_text_included(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        cmd = self._call_args()
        idx_url = cmd.index("--media")
        self.assertEqual(cmd[idx_url + 1], SAMPLE_URL)
        idx_text = cmd.index("--text")
        self.assertEqual(cmd[idx_text + 1], SAMPLE_CAPTION)


# ---------------------------------------------------------------------------
# ValueError guard
# ---------------------------------------------------------------------------
class TestValueErrorGuard(unittest.TestCase):
    def setUp(self):
        patcher_zernio = mock.patch("scripts.post_utils.ZERNI0", "zernio")
        patcher_zernio.start()
        self.addCleanup(patcher_zernio.stop)

    def test_draft_false_and_no_scheduled_at_raises(self):
        with self.assertRaises(ValueError) as ctx:
            create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=False)
        self.assertIn("draft=True", str(ctx.exception))

    def test_draft_true_without_scheduled_at_ok(self):
        with mock.patch("scripts.post_utils.subprocess.run", return_value=mock.Mock(returncode=0)):
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        self.assertTrue(result)

    def test_draft_false_with_scheduled_at_ok(self):
        with mock.patch("scripts.post_utils.subprocess.run", return_value=mock.Mock(returncode=0)):
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, SAMPLE_TIME)
        self.assertTrue(result)

    def test_empty_scheduled_at_without_draft_raises(self):
        with self.assertRaises(ValueError):
            create_post(SAMPLE_URL, SAMPLE_CAPTION, scheduled_at="")


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
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, max_retries=2, retry_delay=0)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Rate-limit retry
# ---------------------------------------------------------------------------
class TestRateLimitRetry(unittest.TestCase):
    def setUp(self):
        patcher_zernio = mock.patch("scripts.post_utils.ZERNI0", "zernio")
        patcher_zernio.start()
        self.addCleanup(patcher_zernio.stop)

    def test_retries_on_429_in_stderr(self):
        rate_limited = mock.Mock(returncode=1, stdout="", stderr="HTTP 429 Too Many Requests")
        success = mock.Mock(returncode=0)
        with mock.patch("scripts.post_utils.subprocess.run", side_effect=[rate_limited, success]) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, retry_delay=0)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            m_sleep.assert_called_once_with(60)

    def test_retries_on_429_in_stdout(self):
        rate_limited = mock.Mock(returncode=1, stdout="rate limit exceeded", stderr="")
        success = mock.Mock(returncode=0)
        with mock.patch("scripts.post_utils.subprocess.run", side_effect=[rate_limited, success]) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, retry_delay=0)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            m_sleep.assert_called_once_with(60)

    def test_single_retry_succeeds(self):
        fail = mock.Mock(returncode=1, stdout="something broke", stderr="")
        success = mock.Mock(returncode=0)
        with mock.patch("scripts.post_utils.subprocess.run", side_effect=[fail, success]) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, retry_delay=0)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            m_sleep.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
