"""
Tests for element_detector.py changes introduced in this PR.

Changes covered:
- detect_and_annotate_elements: exception now silenced (no print); returns screenshot_path
- annotate_elements_with_positions: exception now silenced (no print); returns screenshot_path
- get_element_positions_from_browser: exception now silenced (no print); returns {}
- create_annotated_screenshot: exception now silenced (no print); returns None
  Also: removed "No elements detected" print when positions is empty
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Stub numpy and PIL before importing the module so we don't need heavy deps.
# ---------------------------------------------------------------------------
_STUBS = ["numpy", "cv2"]
for _mod in _STUBS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# We keep PIL real (it's in requirements.txt) but fall back to a mock if absent.
try:
    from PIL import Image as _real_pil_image
    _PIL_AVAILABLE = True
except ImportError:
    sys.modules["PIL"] = MagicMock()
    sys.modules["PIL.Image"] = MagicMock()
    sys.modules["PIL.ImageDraw"] = MagicMock()
    sys.modules["PIL.ImageFont"] = MagicMock()
    _PIL_AVAILABLE = False

from element_detector import ElementDetector  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tiny_png(path):
    """Write a valid 1×1 white PNG to *path* using PIL or raw bytes."""
    if _PIL_AVAILABLE:
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img.save(path)
    else:
        # Minimal valid PNG (1x1 white pixel, pre-built)
        _TINY_PNG = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with open(path, "wb") as f:
            f.write(_TINY_PNG)


# ---------------------------------------------------------------------------
# detect_and_annotate_elements
# ---------------------------------------------------------------------------

class TestDetectAndAnnotateElementsSilencedExceptions(unittest.TestCase):
    """Verify that detect_and_annotate_elements silences exceptions and
    returns the original screenshot_path without printing anything."""

    def setUp(self):
        self.detector = ElementDetector()

    def test_returns_original_path_when_file_missing(self):
        """Returns screenshot_path when the screenshot file does not exist."""
        result = self.detector.detect_and_annotate_elements(
            "/nonexistent/shot.png", browser_automation=None
        )
        self.assertEqual(result, "/nonexistent/shot.png")

    def test_no_print_when_file_missing(self):
        """No output is printed to stdout/stderr when the file is missing."""
        with patch("builtins.print") as mock_print:
            self.detector.detect_and_annotate_elements(
                "/nonexistent/shot.png", browser_automation=None
            )
        mock_print.assert_not_called()

    def test_returns_original_path_when_image_open_raises(self):
        """Returns screenshot_path when PIL raises during Image.open."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write garbage so PIL raises
            f.write(b"not a real image")
            path = f.name
        try:
            result = self.detector.detect_and_annotate_elements(path, browser_automation=None)
            self.assertEqual(result, path)
        finally:
            os.unlink(path)

    def test_no_print_when_image_open_raises(self):
        """No output printed when PIL raises during Image.open."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"garbage bytes")
            path = f.name
        try:
            with patch("builtins.print") as mock_print:
                self.detector.detect_and_annotate_elements(path, browser_automation=None)
            mock_print.assert_not_called()
        finally:
            os.unlink(path)

    @unittest.skipUnless(_PIL_AVAILABLE, "PIL not installed")
    def test_returns_annotated_path_on_success(self):
        """Returns the '_annotated' path when annotation succeeds."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_path = os.path.join(tmp_dir, "shot.png")
            _make_tiny_png(shot_path)
            result = self.detector.detect_and_annotate_elements(
                shot_path, browser_automation=None
            )
            expected = os.path.join(tmp_dir, "shot_annotated.png")
            self.assertEqual(result, expected)
            self.assertTrue(os.path.exists(expected))

    @unittest.skipUnless(_PIL_AVAILABLE, "PIL not installed")
    def test_annotates_elements_when_browser_provides_positions(self):
        """Elements from browser_automation are annotated on the image."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_path = os.path.join(tmp_dir, "shot.png")
            _make_tiny_png(shot_path)

            mock_browser = MagicMock()
            mock_browser.session_id = "sess"
            mock_browser.get_interactable_elements.return_value = {
                1: {"x": 5, "y": 5, "width": 20, "height": 20, "tagName": "A", "type": "", "text": ""},
            }

            result = self.detector.detect_and_annotate_elements(shot_path, mock_browser)
            self.assertIn("_annotated", result)

    def test_returns_original_when_browser_raises_exception(self):
        """If get_element_positions_from_browser raises, original path is returned."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"not a real image")
            path = f.name
        try:
            mock_browser = MagicMock()
            mock_browser.session_id = "sess"
            mock_browser.get_interactable_elements.side_effect = RuntimeError("fail")
            result = self.detector.detect_and_annotate_elements(path, mock_browser)
            self.assertEqual(result, path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# annotate_elements_with_positions
# ---------------------------------------------------------------------------

class TestAnnotateElementsWithPositionsSilencedExceptions(unittest.TestCase):
    """Verify that annotate_elements_with_positions silences exceptions."""

    def setUp(self):
        self.detector = ElementDetector()

    def test_returns_original_path_when_file_missing(self):
        """Returns screenshot_path when the file does not exist."""
        result = self.detector.annotate_elements_with_positions(
            "/nonexistent/shot.png", {1: (10, 10, 50, 30)}
        )
        self.assertEqual(result, "/nonexistent/shot.png")

    def test_no_print_when_file_missing(self):
        """No output printed when the file does not exist."""
        with patch("builtins.print") as mock_print:
            self.detector.annotate_elements_with_positions(
                "/nonexistent/shot.png", {1: (10, 10, 50, 30)}
            )
        mock_print.assert_not_called()

    def test_returns_original_path_when_image_corrupt(self):
        """Returns screenshot_path when PIL raises for corrupt image data."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"corrupt data")
            path = f.name
        try:
            result = self.detector.annotate_elements_with_positions(
                path, {1: (0, 0, 10, 10)}
            )
            self.assertEqual(result, path)
        finally:
            os.unlink(path)

    def test_no_print_when_image_corrupt(self):
        """No output printed when PIL raises for corrupt image data."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"corrupt data")
            path = f.name
        try:
            with patch("builtins.print") as mock_print:
                self.detector.annotate_elements_with_positions(path, {})
            mock_print.assert_not_called()
        finally:
            os.unlink(path)

    @unittest.skipUnless(_PIL_AVAILABLE, "PIL not installed")
    def test_returns_annotated_path_on_success(self):
        """Returns the '_annotated' path when annotation succeeds."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_path = os.path.join(tmp_dir, "shot.png")
            _make_tiny_png(shot_path)
            result = self.detector.annotate_elements_with_positions(
                shot_path, {1: (5, 5, 20, 20)}
            )
            expected = os.path.join(tmp_dir, "shot_annotated.png")
            self.assertEqual(result, expected)
            self.assertTrue(os.path.exists(expected))

    @unittest.skipUnless(_PIL_AVAILABLE, "PIL not installed")
    def test_annotated_file_created_on_disk(self):
        """The annotated image file is actually written to disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_path = os.path.join(tmp_dir, "s.png")
            _make_tiny_png(shot_path)
            self.detector.annotate_elements_with_positions(
                shot_path, {1: (0, 0, 10, 10), 2: (20, 20, 15, 15)}
            )
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, "s_annotated.png")))

    @unittest.skipUnless(_PIL_AVAILABLE, "PIL not installed")
    def test_empty_positions_dict_still_succeeds(self):
        """Empty element_positions dict causes no annotation but returns annotated path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_path = os.path.join(tmp_dir, "empty.png")
            _make_tiny_png(shot_path)
            result = self.detector.annotate_elements_with_positions(shot_path, {})
            # Should still produce the annotated path (no elements but success)
            self.assertIn("_annotated", result)


# ---------------------------------------------------------------------------
# get_element_positions_from_browser
# ---------------------------------------------------------------------------

class TestGetElementPositionsFromBrowser(unittest.TestCase):
    """Tests for get_element_positions_from_browser with silent exceptions."""

    def setUp(self):
        self.detector = ElementDetector()

    def test_returns_empty_dict_when_browser_is_none(self):
        """Returns {} when browser_automation is None."""
        result = self.detector.get_element_positions_from_browser(None)
        self.assertEqual(result, {})

    def test_returns_empty_dict_when_session_id_is_none(self):
        """Returns {} when browser_automation.session_id is None."""
        mock_browser = MagicMock()
        mock_browser.session_id = None
        result = self.detector.get_element_positions_from_browser(mock_browser)
        self.assertEqual(result, {})

    def test_returns_empty_dict_on_exception(self):
        """Returns {} (does not raise, does not print) when get_interactable_elements raises."""
        mock_browser = MagicMock()
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.side_effect = RuntimeError("oops")
        result = self.detector.get_element_positions_from_browser(mock_browser)
        self.assertEqual(result, {})

    def test_no_print_on_exception(self):
        """No output is printed to stdout/stderr when an exception occurs."""
        mock_browser = MagicMock()
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.side_effect = RuntimeError("oops")
        with patch("builtins.print") as mock_print:
            self.detector.get_element_positions_from_browser(mock_browser)
        mock_print.assert_not_called()

    def test_returns_positions_from_element_map(self):
        """Correctly extracts (x, y, width, height) tuples from the element map."""
        mock_browser = MagicMock()
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.return_value = {
            1: {"x": 10, "y": 20, "width": 100, "height": 30, "tagName": "A"},
            2: {"x": 50, "y": 80, "width": 120, "height": 40, "tagName": "BUTTON"},
        }
        result = self.detector.get_element_positions_from_browser(mock_browser)
        self.assertEqual(result[1], (10, 20, 100, 30))
        self.assertEqual(result[2], (50, 80, 120, 40))

    def test_skips_malformed_elements(self):
        """Elements missing required keys are skipped without raising."""
        mock_browser = MagicMock()
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.return_value = {
            1: {"x": 10, "y": 20, "width": 100, "height": 30},  # valid
            2: {"tagName": "A"},  # missing x, y, width, height → skipped
        }
        result = self.detector.get_element_positions_from_browser(mock_browser)
        self.assertIn(1, result)
        self.assertNotIn(2, result)

    def test_returns_empty_dict_when_element_map_empty(self):
        """Returns {} when get_interactable_elements returns an empty dict."""
        mock_browser = MagicMock()
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.return_value = {}
        result = self.detector.get_element_positions_from_browser(mock_browser)
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# create_annotated_screenshot
# ---------------------------------------------------------------------------

class TestCreateAnnotatedScreenshot(unittest.TestCase):
    """Tests for create_annotated_screenshot with silent exceptions and
    the removed 'No elements detected' print."""

    def setUp(self):
        self.detector = ElementDetector()

    def test_returns_none_on_exception(self):
        """Returns None (does not raise) when browser_automation is None."""
        result = self.detector.create_annotated_screenshot(None)
        self.assertIsNone(result)

    def test_no_print_on_exception_when_browser_none(self):
        """No output is printed when browser_automation is None."""
        with patch("builtins.print") as mock_print:
            self.detector.create_annotated_screenshot(None)
        mock_print.assert_not_called()

    def test_returns_none_when_take_screenshot_raises(self):
        """Returns None when browser_automation.take_screenshot() raises."""
        mock_browser = MagicMock()
        mock_browser.take_screenshot.side_effect = RuntimeError("screenshot failed")
        result = self.detector.create_annotated_screenshot(mock_browser)
        self.assertIsNone(result)

    def test_no_print_when_take_screenshot_raises(self):
        """No output is printed when take_screenshot raises."""
        mock_browser = MagicMock()
        mock_browser.take_screenshot.side_effect = RuntimeError("fail")
        with patch("builtins.print") as mock_print:
            self.detector.create_annotated_screenshot(mock_browser)
        mock_print.assert_not_called()

    def test_returns_screenshot_path_when_no_positions(self):
        """Returns the raw screenshot_path when get_element_positions_from_browser
        returns an empty dict (positions is falsy).  No print is emitted."""
        mock_browser = MagicMock()
        mock_browser.take_screenshot.return_value = "/tmp/shot.png"
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.return_value = {}

        result = self.detector.create_annotated_screenshot(mock_browser)
        self.assertEqual(result, "/tmp/shot.png")

    def test_no_print_when_no_positions(self):
        """The removed 'No elements detected for annotation' print is no longer emitted."""
        mock_browser = MagicMock()
        mock_browser.take_screenshot.return_value = "/tmp/shot.png"
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.return_value = {}

        with patch("builtins.print") as mock_print:
            self.detector.create_annotated_screenshot(mock_browser)
        mock_print.assert_not_called()

    @unittest.skipUnless(_PIL_AVAILABLE, "PIL not installed")
    def test_returns_annotated_path_when_positions_available(self):
        """Returns annotated path when positions are available and annotation succeeds."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            shot_path = os.path.join(tmp_dir, "shot.png")
            _make_tiny_png(shot_path)

            mock_browser = MagicMock()
            mock_browser.take_screenshot.return_value = shot_path
            mock_browser.session_id = "sess"
            mock_browser.get_interactable_elements.return_value = {
                1: {"x": 5, "y": 5, "width": 20, "height": 20, "tagName": "A", "type": "", "text": ""},
            }

            result = self.detector.create_annotated_screenshot(mock_browser)
            self.assertIsNotNone(result)
            self.assertIn("_annotated", result)

    def test_no_print_when_annotation_raises(self):
        """No output is printed when annotate_elements_with_positions raises."""
        mock_browser = MagicMock()
        mock_browser.take_screenshot.return_value = "/tmp/shot.png"
        mock_browser.session_id = "sess"
        mock_browser.get_interactable_elements.return_value = {
            1: {"x": 0, "y": 0, "width": 10, "height": 10}
        }

        with patch.object(
            self.detector, "get_element_positions_from_browser", return_value={1: (0, 0, 10, 10)}
        ), patch.object(
            self.detector, "annotate_elements_with_positions", side_effect=RuntimeError("draw fail")
        ), patch("builtins.print") as mock_print:
            self.detector.create_annotated_screenshot(mock_browser)
        mock_print.assert_not_called()

    def test_returns_none_when_annotation_raises(self):
        """Returns None when annotate_elements_with_positions raises."""
        mock_browser = MagicMock()
        mock_browser.take_screenshot.return_value = "/tmp/shot.png"
        mock_browser.session_id = "sess"

        with patch.object(
            self.detector, "get_element_positions_from_browser", return_value={1: (0, 0, 10, 10)}
        ), patch.object(
            self.detector, "annotate_elements_with_positions", side_effect=RuntimeError("draw fail")
        ):
            result = self.detector.create_annotated_screenshot(mock_browser)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()