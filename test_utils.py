"""
Tests for utils.py changes introduced in this PR.

Changes covered:
- save_json_data: exception now silenced (returns False, no print)
- load_json_data: exception now silenced (returns None, no print)
- clean_old_screenshots: prints removed, exception silenced
- get_system_info: REMOVED - verify absence
- log_automation_step: REMOVED - verify absence
"""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

import utils
from utils import (
    save_json_data,
    load_json_data,
    clean_old_screenshots,
    format_error_message,
)


# ---------------------------------------------------------------------------
# save_json_data
# ---------------------------------------------------------------------------

class TestSaveJsonData(unittest.TestCase):
    """Tests for save_json_data with silenced exception handling."""

    def test_saves_dict_and_returns_true(self):
        """Returns True when data is saved successfully."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = save_json_data({"key": "value"}, path)
            self.assertTrue(result)
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, {"key": "value"})
        finally:
            os.unlink(path)

    def test_saves_list_data(self):
        """Returns True when list data is saved successfully."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = save_json_data([1, 2, 3], path)
            self.assertTrue(result)
        finally:
            os.unlink(path)

    def test_saves_nested_structure(self):
        """Nested dicts and lists are serialised correctly."""
        data = {"a": [1, 2], "b": {"c": True}}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_json_data(data, path)
            with open(path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), data)
        finally:
            os.unlink(path)

    def test_returns_false_on_io_error(self):
        """Returns False (does not raise, does not print) when write fails."""
        result = save_json_data({"x": 1}, "/nonexistent_dir/no_file.json")
        self.assertFalse(result)

    def test_no_print_on_failure(self):
        """No output is printed to stdout/stderr when an exception occurs."""
        with patch("builtins.print") as mock_print:
            save_json_data({}, "/nonexistent_dir/no_file.json")
        mock_print.assert_not_called()

    def test_uses_default_str_for_non_serialisable(self):
        """Non-JSON-serialisable values are coerced via default=str."""
        from datetime import datetime
        data = {"ts": datetime(2024, 1, 1)}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = save_json_data(data, path)
            self.assertTrue(result)
        finally:
            os.unlink(path)

    def test_file_written_with_indentation(self):
        """Output file uses indent=2 for human-readable formatting."""
        data = {"key": "value"}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_json_data(data, path)
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            # indent=2 means the first key is indented with 2 spaces
            self.assertIn("  ", raw)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# load_json_data
# ---------------------------------------------------------------------------

class TestLoadJsonData(unittest.TestCase):
    """Tests for load_json_data with silenced exception handling."""

    def test_loads_dict_correctly(self):
        """Returns parsed dict for a valid JSON file."""
        data = {"hello": "world", "num": 42}
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_json_data(path)
            self.assertEqual(result, data)
        finally:
            os.unlink(path)

    def test_loads_list_correctly(self):
        """Returns parsed list for a valid JSON file containing a list."""
        data = [1, "two", 3.0]
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_json_data(path)
            self.assertEqual(result, data)
        finally:
            os.unlink(path)

    def test_returns_none_for_missing_file(self):
        """Returns None (does not raise) when the file does not exist."""
        result = load_json_data("/nonexistent_path/missing.json")
        self.assertIsNone(result)

    def test_returns_none_for_invalid_json(self):
        """Returns None (does not raise) when the file contains invalid JSON."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write("{ not valid json }")
            path = f.name
        try:
            result = load_json_data(path)
            self.assertIsNone(result)
        finally:
            os.unlink(path)

    def test_no_print_on_failure(self):
        """No output is printed to stdout/stderr when an exception occurs."""
        with patch("builtins.print") as mock_print:
            load_json_data("/nonexistent_path/missing.json")
        mock_print.assert_not_called()

    def test_returns_none_for_empty_file(self):
        """Returns None for a completely empty file (json.JSONDecodeError)."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            path = f.name  # write nothing
        try:
            result = load_json_data(path)
            self.assertIsNone(result)
        finally:
            os.unlink(path)

    def test_roundtrip_with_save_json_data(self):
        """Data saved by save_json_data is correctly loaded back."""
        data = {"roundtrip": True, "items": [1, 2, 3]}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_json_data(data, path)
            result = load_json_data(path)
            self.assertEqual(result, data)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# clean_old_screenshots
# ---------------------------------------------------------------------------

class TestCleanOldScreenshots(unittest.TestCase):
    """Tests for clean_old_screenshots with prints removed and exceptions silenced."""

    def _make_screenshot_dir(self, tmp_dir, names):
        """Helper: create dummy image files in tmp_dir and return the dir path."""
        for name in names:
            open(os.path.join(tmp_dir, name), "wb").close()
        return tmp_dir

    def test_does_nothing_if_directory_missing(self):
        """Returns without error when the directory does not exist."""
        clean_old_screenshots(directory="/nonexistent_screenshots_dir_xyz", max_files=5)
        # No assertion needed; we just verify no exception is raised.

    def test_does_nothing_when_under_limit(self):
        """Does not delete files when count is within max_files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            names = [f"screenshot_{i:03d}.png" for i in range(3)]
            self._make_screenshot_dir(tmp_dir, names)
            clean_old_screenshots(directory=tmp_dir, max_files=5)
            remaining = os.listdir(tmp_dir)
            self.assertEqual(len(remaining), 3)

    def test_removes_oldest_files_when_over_limit(self):
        """Removes the oldest files when count exceeds max_files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create files with controlled creation times (sleep to differ)
            paths = []
            for i in range(5):
                p = os.path.join(tmp_dir, f"shot_{i:03d}.png")
                open(p, "wb").close()
                paths.append(p)
                # Small delay so ctime differs; if OS resolution is coarse, touch mtime
                os.utime(p, (time.time() + i, time.time() + i))

            clean_old_screenshots(directory=tmp_dir, max_files=3)
            remaining = sorted(os.listdir(tmp_dir))
            # Only 3 files should remain
            self.assertEqual(len(remaining), 3)

    def test_only_processes_image_extensions(self):
        """Non-image files are not considered or deleted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create image files and a non-image file
            for i in range(6):
                open(os.path.join(tmp_dir, f"shot_{i:03d}.png"), "wb").close()
            open(os.path.join(tmp_dir, "notes.txt"), "w").close()

            clean_old_screenshots(directory=tmp_dir, max_files=3)
            remaining = os.listdir(tmp_dir)
            # The txt file must survive regardless
            self.assertIn("notes.txt", remaining)

    def test_handles_mixed_image_extensions(self):
        """All supported image extensions (.png, .jpg, .jpeg, .webp) are considered."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            exts = [".png", ".jpg", ".jpeg", ".webp", ".png"]
            for i, ext in enumerate(exts):
                p = os.path.join(tmp_dir, f"shot_{i:03d}{ext}")
                open(p, "wb").close()
                os.utime(p, (time.time() + i, time.time() + i))

            clean_old_screenshots(directory=tmp_dir, max_files=2)
            remaining = os.listdir(tmp_dir)
            self.assertEqual(len(remaining), 2)

    def test_no_print_output(self):
        """No output is printed to stdout/stderr during execution."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i in range(3):
                open(os.path.join(tmp_dir, f"shot_{i:03d}.png"), "wb").close()
            with patch("builtins.print") as mock_print:
                clean_old_screenshots(directory=tmp_dir, max_files=1)
            mock_print.assert_not_called()

    def test_silences_os_remove_failure(self):
        """Does not raise if os.remove fails (inner exception is silenced)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i in range(5):
                open(os.path.join(tmp_dir, f"shot_{i:03d}.png"), "wb").close()
            with patch("os.remove", side_effect=OSError("permission denied")):
                # Should not raise
                clean_old_screenshots(directory=tmp_dir, max_files=2)

    def test_silences_outer_exception(self):
        """Outer exceptions (e.g., from os.listdir) are silenced without raising."""
        with patch("os.path.exists", return_value=True), \
             patch("os.listdir", side_effect=PermissionError("denied")):
            clean_old_screenshots(directory="/some/dir", max_files=5)
        # No exception should propagate


# ---------------------------------------------------------------------------
# Removed functions - verify they no longer exist in the module
# ---------------------------------------------------------------------------

class TestRemovedFunctions(unittest.TestCase):
    """Verify that functions deleted in this PR are no longer present in utils."""

    def test_get_system_info_removed(self):
        """get_system_info was deleted in this PR and must not exist."""
        self.assertFalse(
            hasattr(utils, "get_system_info"),
            "get_system_info should have been removed from utils.py",
        )

    def test_log_automation_step_removed(self):
        """log_automation_step was deleted in this PR and must not exist."""
        self.assertFalse(
            hasattr(utils, "log_automation_step"),
            "log_automation_step should have been removed from utils.py",
        )


# ---------------------------------------------------------------------------
# format_error_message (boundary / regression cases)
# ---------------------------------------------------------------------------

class TestFormatErrorMessage(unittest.TestCase):
    """Regression tests for format_error_message (unchanged logic, in scope as
    it lives in the modified file). Extra boundary cases for confidence."""

    def test_connection_refused_keyword(self):
        """Matches 'connection refused' case-insensitively."""
        msg = format_error_message(Exception("Connection Refused"), "ctx")
        self.assertIn("Unable to connect", msg)

    def test_timeout_keyword(self):
        """Matches 'timeout' in the error string."""
        msg = format_error_message(Exception("operation Timeout occurred"), "")
        self.assertIn("timed out", msg)

    def test_not_found_keyword(self):
        """Matches 'not found' in the error string."""
        msg = format_error_message(Exception("Resource Not Found"), "")
        self.assertIn("not found", msg)

    def test_permission_denied_keyword(self):
        """Matches 'permission denied' in the error string."""
        msg = format_error_message(Exception("Permission Denied"), "")
        self.assertIn("Permission denied", msg)

    def test_generic_error_fallback(self):
        """Falls back to the generic template when no keyword matches."""
        msg = format_error_message(Exception("something unexpected"), "")
        self.assertIn("An error occurred", msg)

    def test_context_included_in_output(self):
        """The context string appears somewhere in the returned message."""
        msg = format_error_message(Exception("timeout"), "please retry")
        self.assertIn("please retry", msg)

    def test_empty_context(self):
        """Empty context string does not cause errors."""
        msg = format_error_message(Exception("timeout"), "")
        self.assertIsInstance(msg, str)

    def test_non_exception_error_object(self):
        """Accepts any object with a str() representation."""
        msg = format_error_message("connection refused", "")
        self.assertIn("Unable to connect", msg)


if __name__ == "__main__":
    unittest.main()
