"""
Tests for browser_automation.py changes introduced in this PR.

Changes covered:
- start_browser: print statements removed (session start + failure); re-raises exception
- take_screenshot: removed debug prints for image header/format; image format
  detection exception now silently falls back to "png" (no print warning)
- get_interactable_elements: removed print on error; still returns {} on exception
- close: removed "Firecrawl browser session closed" print
"""
import base64
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# Stub heavy dependencies before importing the module under test.
# ---------------------------------------------------------------------------
_STUBS = ["firecrawl", "PIL", "PIL.Image", "cv2"]
for _mod in _STUBS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from browser_automation import BrowserAutomation  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_automation(api_key="test_key"):
    """Return a BrowserAutomation with a mocked FirecrawlApp."""
    with patch("browser_automation.FirecrawlApp"):
        ba = BrowserAutomation(api_key=api_key)
        ba.app = MagicMock()
    return ba


def _png_magic_bytes():
    """89 50 4E 47 0D 0A 1A 0A — PNG magic bytes, padded to 16 bytes."""
    return bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 8


def _jpeg_magic_bytes():
    """FF D8 FF — JPEG magic bytes, padded to 16 bytes."""
    return bytes.fromhex("ffd8ff") + b"\x00" * 13


def _webp_magic_bytes():
    """RIFF????WEBP — WebP magic bytes, exactly 16 bytes."""
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 4


def _make_b64(raw_bytes):
    """Encode bytes as a base64 string."""
    return base64.b64encode(raw_bytes).decode()


def _run_screenshot_with_bytes(ba, raw_bytes):
    """
    Execute ba.take_screenshot() with the given raw image bytes as the mocked
    return value, redirecting file writes to a real temporary directory.

    Returns the path returned by take_screenshot().
    """
    b64_data = _make_b64(raw_bytes)
    ba.app.browser_execute.return_value.success = True
    ba.app.browser_execute.return_value.result = b64_data
    ba.app.browser_execute.return_value.stdout = None

    with tempfile.TemporaryDirectory() as tmp_dir:
        original_join = os.path.join

        def _patched_join(*args):
            # Redirect screenshots/ directory to tmp_dir
            if args and args[0] == "screenshots":
                return original_join(tmp_dir, *args[1:])
            return original_join(*args)

        with patch("os.path.join", side_effect=_patched_join), \
             patch("os.makedirs"):
            path = ba.take_screenshot()

    return path


# ---------------------------------------------------------------------------
# BrowserAutomation.__init__
# ---------------------------------------------------------------------------

class TestBrowserAutomationInit(unittest.TestCase):
    """Constructor behaviour."""

    def test_raises_without_api_key(self):
        """ValueError is raised when no API key is supplied."""
        with self.assertRaises(ValueError):
            BrowserAutomation(api_key=None)

    def test_raises_with_empty_api_key(self):
        """ValueError is raised when an empty string API key is supplied."""
        with self.assertRaises(ValueError):
            BrowserAutomation(api_key="")

    def test_initial_session_id_none(self):
        """session_id starts as None."""
        ba = _make_automation()
        self.assertIsNone(ba.session_id)

    def test_initial_screenshot_counter(self):
        """screenshot_counter starts at 1."""
        ba = _make_automation()
        self.assertEqual(ba.screenshot_counter, 1)

    def test_initial_element_map_empty(self):
        """element_map starts as an empty dict."""
        ba = _make_automation()
        self.assertEqual(ba.element_map, {})


# ---------------------------------------------------------------------------
# start_browser
# ---------------------------------------------------------------------------

class TestStartBrowser(unittest.TestCase):
    """Tests for start_browser with prints removed."""

    def setUp(self):
        self.ba = _make_automation()

    def _attr_response(self, session_id):
        resp = MagicMock()
        resp.id = session_id
        return resp

    def _dict_response(self, session_id):
        return {"id": session_id}

    def test_returns_true_on_success(self):
        """Returns True when a valid session_id is obtained."""
        self.ba.app.browser.return_value = self._attr_response("sess_123")
        with patch.object(self.ba, "navigate_to"):
            result = self.ba.start_browser()
        self.assertTrue(result)

    def test_sets_session_id_from_attribute(self):
        """session_id is read from response.id."""
        self.ba.app.browser.return_value = self._attr_response("attr_id")
        with patch.object(self.ba, "navigate_to"):
            self.ba.start_browser()
        self.assertEqual(self.ba.session_id, "attr_id")

    def test_sets_session_id_from_dict(self):
        """session_id is read from response['id'] when response is a dict."""
        self.ba.app.browser.return_value = self._dict_response("dict_id")
        with patch.object(self.ba, "navigate_to"):
            self.ba.start_browser()
        self.assertEqual(self.ba.session_id, "dict_id")

    def test_raises_when_session_id_missing(self):
        """Exception propagates when no session_id can be obtained."""
        # Response with no 'id' attribute and not a dict
        resp = MagicMock(spec=[])
        self.ba.app.browser.return_value = resp
        with self.assertRaises(Exception):
            self.ba.start_browser()

    def test_raises_when_browser_call_fails(self):
        """Exception from self.app.browser() propagates to the caller."""
        self.ba.app.browser.side_effect = RuntimeError("network error")
        with self.assertRaises(RuntimeError):
            self.ba.start_browser()

    def test_no_print_on_success(self):
        """No output is printed to stdout/stderr on successful start."""
        self.ba.app.browser.return_value = self._attr_response("ok_sess")
        with patch.object(self.ba, "navigate_to"), \
             patch("builtins.print") as mock_print:
            self.ba.start_browser()
        mock_print.assert_not_called()

    def test_no_print_on_failure(self):
        """No output is printed when start_browser raises."""
        self.ba.app.browser.side_effect = RuntimeError("boom")
        with patch("builtins.print") as mock_print:
            try:
                self.ba.start_browser()
            except RuntimeError:
                pass
        mock_print.assert_not_called()

    def test_navigates_to_google_after_session_start(self):
        """navigate_to is called with the Google URL after obtaining the session."""
        self.ba.app.browser.return_value = self._attr_response("nav_sess")
        with patch.object(self.ba, "navigate_to") as mock_nav:
            self.ba.start_browser()
        mock_nav.assert_called_once_with("https://www.google.com")


# ---------------------------------------------------------------------------
# take_screenshot – image format detection
# ---------------------------------------------------------------------------

class TestTakeScreenshotFormatDetection(unittest.TestCase):
    """Tests for the image format detection logic in take_screenshot."""

    def setUp(self):
        self.ba = _make_automation()
        self.ba.session_id = "active_session"

    def test_detects_png_by_magic_bytes(self):
        """PNG magic bytes → path ends with '.png'."""
        path = _run_screenshot_with_bytes(self.ba, _png_magic_bytes())
        self.assertTrue(path.endswith(".png"), f"Expected .png, got: {path}")

    def test_detects_jpeg_by_magic_bytes(self):
        """JPEG magic bytes → path ends with '.jpeg'."""
        path = _run_screenshot_with_bytes(self.ba, _jpeg_magic_bytes())
        self.assertTrue(path.endswith(".jpeg"), f"Expected .jpeg, got: {path}")

    def test_detects_webp_by_magic_bytes(self):
        """WebP magic bytes → path ends with '.webp'."""
        path = _run_screenshot_with_bytes(self.ba, _webp_magic_bytes())
        self.assertTrue(path.endswith(".webp"), f"Expected .webp, got: {path}")

    def test_falls_back_to_png_on_format_detection_exception(self):
        """When the format detection block raises, extension defaults to 'png'."""
        unknown_bytes = b"\x00\x01\x02\x03" * 16
        with patch("browser_automation.Image") as mock_img_mod:
            mock_img_mod.open.side_effect = Exception("unrecognised format")
            path = _run_screenshot_with_bytes(self.ba, unknown_bytes)
        self.assertTrue(path.endswith(".png"), f"Expected .png fallback, got: {path}")

    def test_no_print_on_format_detection_exception(self):
        """No output is printed when the format detection block raises."""
        unknown_bytes = b"\x00\x01\x02\x03" * 16
        with patch("browser_automation.Image") as mock_img_mod, \
             patch("builtins.print") as mock_print:
            mock_img_mod.open.side_effect = Exception("unrecognised format")
            try:
                _run_screenshot_with_bytes(self.ba, unknown_bytes)
            except Exception:
                pass
        mock_print.assert_not_called()

    def test_raises_when_session_not_started(self):
        """Exception raised if session_id is None (browser not started)."""
        self.ba.session_id = None
        with self.assertRaises(Exception):
            self.ba.take_screenshot()

    def test_raises_on_failed_execute(self):
        """Exception propagates when browser_execute reports failure."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "JS error"
        self.ba.app.browser_execute.return_value = mock_result
        with self.assertRaises(Exception):
            self.ba.take_screenshot()

    def test_raises_when_no_image_data_returned(self):
        """Exception raised when result contains no image data."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = None
        mock_result.stdout = None
        self.ba.app.browser_execute.return_value = mock_result
        with self.assertRaises(Exception):
            self.ba.take_screenshot()

    def test_increments_screenshot_counter(self):
        """screenshot_counter increments by 1 after a successful screenshot."""
        initial = self.ba.screenshot_counter
        _run_screenshot_with_bytes(self.ba, _png_magic_bytes())
        self.assertEqual(self.ba.screenshot_counter, initial + 1)

    def test_no_print_on_success(self):
        """No output is printed to stdout/stderr on a successful screenshot."""
        with patch("builtins.print") as mock_print:
            try:
                _run_screenshot_with_bytes(self.ba, _png_magic_bytes())
            except Exception:
                pass
        mock_print.assert_not_called()

    def test_filename_contains_screenshot_counter(self):
        """The returned filename encodes the screenshot counter value."""
        self.ba.screenshot_counter = 7
        path = _run_screenshot_with_bytes(self.ba, _png_magic_bytes())
        basename = os.path.basename(path)
        self.assertIn("007", basename)


# ---------------------------------------------------------------------------
# get_interactable_elements
# ---------------------------------------------------------------------------

class TestGetInteractableElements(unittest.TestCase):
    """Tests for get_interactable_elements with silent exception handling."""

    def setUp(self):
        self.ba = _make_automation()
        self.ba.session_id = "active_session"

    def test_returns_empty_dict_on_exception(self):
        """Returns {} (does not raise, does not print) when browser_execute raises."""
        self.ba.app.browser_execute.side_effect = RuntimeError("unexpected")
        result = self.ba.get_interactable_elements()
        self.assertEqual(result, {})

    def test_returns_empty_dict_on_failed_execute(self):
        """Returns {} when browser_execute reports success=False."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "JS error"
        self.ba.app.browser_execute.return_value = mock_result
        result = self.ba.get_interactable_elements()
        self.assertEqual(result, {})

    def test_no_print_on_exception(self):
        """No output is printed to stdout/stderr when an exception occurs."""
        self.ba.app.browser_execute.side_effect = RuntimeError("boom")
        with patch("builtins.print") as mock_print:
            self.ba.get_interactable_elements()
        mock_print.assert_not_called()

    def test_raises_when_session_not_started(self):
        """Exception is raised (not silenced) when session_id is None."""
        self.ba.session_id = None
        with self.assertRaises(Exception):
            self.ba.get_interactable_elements()

    def test_builds_element_map_from_result(self):
        """element_map is populated from the elements returned by browser_execute."""
        elements = [
            {"x": 10, "y": 20, "width": 100, "height": 30, "tagName": "A",
             "type": "", "text": "link"},
            {"x": 50, "y": 80, "width": 120, "height": 40, "tagName": "BUTTON",
             "type": "submit", "text": "go"},
        ]
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = elements
        self.ba.app.browser_execute.return_value = mock_result
        result = self.ba.get_interactable_elements()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["tagName"], "A")
        self.assertEqual(result[2]["tagName"], "BUTTON")

    def test_returns_empty_dict_when_elements_none(self):
        """Returns {} when result.result and result.stdout are both falsy."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = None
        mock_result.stdout = None
        self.ba.app.browser_execute.return_value = mock_result
        result = self.ba.get_interactable_elements()
        self.assertEqual(result, {})

    def test_element_map_stored_on_instance(self):
        """Successful call updates self.element_map."""
        elements = [
            {"x": 0, "y": 0, "width": 10, "height": 10, "tagName": "INPUT",
             "type": "text", "text": ""},
        ]
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = elements
        self.ba.app.browser_execute.return_value = mock_result
        self.ba.get_interactable_elements()
        self.assertIn(1, self.ba.element_map)


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

class TestClose(unittest.TestCase):
    """Tests for close() with print statement removed."""

    def setUp(self):
        self.ba = _make_automation()
        self.ba.session_id = "session_to_close"
        self.ba.element_map = {1: {"x": 0}}

    def test_clears_session_id(self):
        """session_id is set to None after close()."""
        self.ba.close()
        self.assertIsNone(self.ba.session_id)

    def test_clears_element_map(self):
        """element_map is reset to an empty dict after close()."""
        self.ba.close()
        self.assertEqual(self.ba.element_map, {})

    def test_calls_delete_browser(self):
        """delete_browser is called with the current session_id."""
        self.ba.close()
        self.ba.app.delete_browser.assert_called_once_with("session_to_close")

    def test_no_print_on_close(self):
        """No output is printed to stdout/stderr when close() is called."""
        with patch("builtins.print") as mock_print:
            self.ba.close()
        mock_print.assert_not_called()

    def test_no_print_when_delete_raises(self):
        """No output is printed even if delete_browser raises."""
        self.ba.app.delete_browser.side_effect = Exception("network error")
        with patch("builtins.print") as mock_print:
            self.ba.close()
        mock_print.assert_not_called()

    def test_still_clears_state_when_delete_raises(self):
        """session_id and element_map are cleared even if delete_browser raises."""
        self.ba.app.delete_browser.side_effect = Exception("oops")
        self.ba.close()
        self.assertIsNone(self.ba.session_id)
        self.assertEqual(self.ba.element_map, {})

    def test_does_nothing_when_already_closed(self):
        """close() is a no-op when session_id is already None."""
        self.ba.session_id = None
        self.ba.close()
        self.ba.app.delete_browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()