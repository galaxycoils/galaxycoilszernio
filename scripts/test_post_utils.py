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

from scripts.post_utils import ACCOUNT_ID, DEDUP_SKIP_CAPTION, apply_dedup_suffix, create_post, create_paired_posts

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

    def test_multiple_accounts_passed_as_list(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, accounts=["acct1", "acct2"])
        cmd = self._call_args()
        self.assertIn("acct1,acct2", cmd)

    def test_multiple_accounts_passed_as_comma_separated_string(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True, accounts="acct1, acct2")
        cmd = self._call_args()
        self.assertIn("acct1,acct2", cmd)

    def test_media_and_text_included(self):
        create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
        cmd = self._call_args()
        idx_url = cmd.index("--media")
        self.assertEqual(cmd[idx_url + 1], SAMPLE_URL)
        idx_text = cmd.index("--text")
        self.assertEqual(cmd[idx_text + 1], SAMPLE_CAPTION)

    def test_dedup_suffix_appended_for_ig(self):
        create_post(SAMPLE_URL, "My caption here for IG", draft=True)
        cmd = self._call_args()
        text = cmd[cmd.index("--text") + 1]
        self.assertTrue(text.startswith("My caption here for IG #"))
        self.assertEqual(len(text.split()[-1]), 7)  # # + 6 hex chars

    def test_dedup_suffix_skipped_for_test_caption(self):
        create_post(SAMPLE_URL, DEDUP_SKIP_CAPTION, draft=True)
        cmd = self._call_args()
        text = cmd[cmd.index("--text") + 1]
        self.assertEqual(text, DEDUP_SKIP_CAPTION)

    def test_reuses_media_url_without_second_upload(self):
        cdn = "https://media.zernio.com/media/test.mp4"
        with mock.patch("scripts.post_utils.ensure_zernio_media_url") as m_upload:
            create_post(None, SAMPLE_CAPTION, draft=True, media_url=cdn)
        m_upload.assert_not_called()
        cmd = self._call_args()
        self.assertIn(cdn, cmd)


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
             mock.patch("scripts.post_utils.time.sleep") as m_sleep, \
             mock.patch("scripts.post_utils.random.randint", return_value=0): # Mock random to 0 for deterministic test
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            # wait_time = 60 * 2^0 + 0 = 60
            m_sleep.assert_called_once_with(60)

    def test_retries_on_500(self):
        server_error = mock.Mock(returncode=1, stdout="500 Internal Server Error", stderr="")
        success = mock.Mock(returncode=0)
        with mock.patch("scripts.post_utils.subprocess.run", side_effect=[server_error, success]) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep, \
             mock.patch("scripts.post_utils.random.randint", return_value=0): # Mock random to 0
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
            self.assertTrue(result)
            self.assertEqual(m_run.call_count, 2)
            # wait_time = 10 * 1 + 0 = 10
            m_sleep.assert_called_once_with(10)

    def test_stops_on_generic_error(self):
        fail = mock.Mock(returncode=1, stdout="something broke", stderr="")
        with mock.patch("scripts.post_utils.subprocess.run", return_value=fail) as m_run, \
             mock.patch("scripts.post_utils.time.sleep") as m_sleep:
            result = create_post(SAMPLE_URL, SAMPLE_CAPTION, draft=True)
            self.assertFalse(result)
            self.assertEqual(m_run.call_count, 1)
            m_sleep.assert_not_called()


class TestApplyDedupSuffix(unittest.TestCase):
    def test_adds_unique_token(self):
        a = apply_dedup_suffix("Hello world test")
        b = apply_dedup_suffix("Hello world test")
        self.assertNotEqual(a, b)

    def test_skips_test_caption(self):
        self.assertEqual(apply_dedup_suffix(DEDUP_SKIP_CAPTION), DEDUP_SKIP_CAPTION)


class TestCreatePairedPosts(unittest.TestCase):
    def setUp(self):
        patcher_zernio = mock.patch("scripts.post_utils.ZERNI0", "zernio")
        patcher_zernio.start()
        self.addCleanup(patcher_zernio.stop)

    def test_uploads_once_creates_two_posts(self):
        cdn = "https://media.zernio.com/media/once.mp4"
        success = mock.Mock(returncode=0, stdout='{"id":"post1"}')
        with mock.patch("scripts.post_utils.ensure_zernio_media_url", return_value=cdn) as m_upload, \
             mock.patch("scripts.post_utils.subprocess.run", return_value=success) as m_run:
            ig_id, th_id = create_paired_posts(
                "https://pexels.com/video/1/file.mp4",
                "IG caption text here",
                "Threads caption text here",
                "2026-06-01T10:00:00.000Z",
            )
        m_upload.assert_called_once()
        self._assert_paired_result(m_run, ig_id, th_id)

    def test_skips_upload_when_media_url_provided(self):
        cdn = "https://media.zernio.com/media/existing.mp4"
        success = mock.Mock(returncode=0, stdout='{"id":"post1"}')
        with mock.patch("scripts.post_utils.ensure_zernio_media_url") as m_upload, \
             mock.patch("scripts.post_utils.subprocess.run", return_value=success) as m_run:
            ig_id, th_id = create_paired_posts(
                None,
                "IG caption text here",
                "Threads caption text here",
                "2026-06-01T10:00:00.000Z",
                media_url=cdn,
            )
        m_upload.assert_not_called()
        self._assert_paired_result(m_run, ig_id, th_id)
        for call in m_run.call_args_list:
            cmd = call[0][0]
            self.assertIn(cdn, cmd)

    def _assert_paired_result(self, m_run, ig_id, th_id):
        self.assertEqual(m_run.call_count, 2)
        self.assertTrue(ig_id)
        self.assertTrue(th_id)
        texts = []
        for call in m_run.call_args_list:
            cmd = call[0][0]
            texts.append(cmd[cmd.index("--text") + 1])
        self.assertNotEqual(texts[0], texts[1])


if __name__ == "__main__":
    unittest.main()
