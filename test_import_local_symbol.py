"""
Tests for the _import_local_symbol function introduced in app.py.

The function provides a resilient importlib.import_module wrapper that retries
once on KeyError (a Python 3.14 import-system edge-case).

Because app.py imports heavyweight Streamlit packages at the top level we
pre-populate sys.modules with lightweight MagicMock stand-ins before importing
the module under test.
"""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Patch every top-level dependency that app.py tries to import before we
# import the module itself.  This keeps the test environment hermetic.
# ---------------------------------------------------------------------------
_STUB_MODULES = [
    "streamlit",
    "extra_streamlit_components",
    "streamlit_local_storage",
    "browser_automation",
    "mistral_client",
    "fireworks_client",
    "element_detector",
    "cv2",
    "PIL",
    "PIL.Image",
    "firecrawl",
    "requests",
]

for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

# Provide realistic-looking class objects so that the module-level calls to
# _import_local_symbol("browser_automation", "BrowserAutomation") etc. return
# something plausible without error.
sys.modules["browser_automation"].BrowserAutomation = MagicMock(name="BrowserAutomation")
sys.modules["mistral_client"].MistralClient = MagicMock(name="MistralClient")
sys.modules["fireworks_client"].FireworksClient = MagicMock(name="FireworksClient")
sys.modules["element_detector"].ElementDetector = MagicMock(name="ElementDetector")

# Streamlit needs a usable session_state mapping; some code paths touch it.
import streamlit as st  # noqa: E402  (already mocked)
st.session_state = {}  # type: ignore[assignment]

# Now it is safe to import the module under test.
import app  # noqa: E402
from app import _import_local_symbol  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_module(name: str, **attrs) -> types.ModuleType:
    """Create a real types.ModuleType populated with the given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestImportLocalSymbolSuccess(unittest.TestCase):
    """Happy-path: module imports cleanly and symbol exists."""

    def test_returns_correct_symbol(self):
        """Symbol is retrieved from the successfully imported module."""
        sentinel = object()
        fake_mod = _make_module("fake_module", MyClass=sentinel)

        with patch("importlib.import_module", return_value=fake_mod) as mock_import:
            result = _import_local_symbol("fake_module", "MyClass")

        self.assertIs(result, sentinel)
        mock_import.assert_called_once_with("fake_module")

    def test_import_called_with_correct_module_name(self):
        """importlib.import_module receives exactly the module_name argument."""
        fake_mod = _make_module("my_pkg.my_mod", Foo=42)

        with patch("importlib.import_module", return_value=fake_mod) as mock_import:
            _import_local_symbol("my_pkg.my_mod", "Foo")

        mock_import.assert_called_once_with("my_pkg.my_mod")

    def test_returns_non_class_symbol(self):
        """Works for any attribute type, not only classes."""
        fake_mod = _make_module("constants_mod", ANSWER=42)

        with patch("importlib.import_module", return_value=fake_mod):
            result = _import_local_symbol("constants_mod", "ANSWER")

        self.assertEqual(result, 42)


class TestImportLocalSymbolKeyErrorRetry(unittest.TestCase):
    """Retry behaviour on first-attempt KeyError (Python 3.14 edge-case)."""

    def test_retries_on_key_error_and_succeeds(self):
        """If the first import raises KeyError, the function retries and returns the symbol."""
        sentinel = object()
        fake_mod = _make_module("flaky_mod", Widget=sentinel)

        side_effects = [KeyError("flaky_mod"), fake_mod]

        with patch("importlib.import_module", side_effect=side_effects) as mock_import:
            result = _import_local_symbol("flaky_mod", "Widget")

        self.assertIs(result, sentinel)
        self.assertEqual(mock_import.call_count, 2)
        mock_import.assert_called_with("flaky_mod")  # last call

    def test_module_removed_from_sys_modules_before_retry(self):
        """On KeyError the half-loaded entry is popped from sys.modules before retry."""
        fake_mod = _make_module("half_loaded", X=1)
        # Pre-populate sys.modules with a sentinel to confirm it is removed.
        sentinel_entry = object()
        sys.modules["half_loaded"] = sentinel_entry  # type: ignore[assignment]

        captured_state: dict = {}

        def _import_side_effect(name):
            if _import_side_effect.call_count == 0:
                _import_side_effect.call_count += 1
                raise KeyError(name)
            # On retry: record whether the stale entry was removed.
            captured_state["has_entry"] = "half_loaded" in sys.modules
            _import_side_effect.call_count += 1
            return fake_mod

        _import_side_effect.call_count = 0

        with patch("importlib.import_module", side_effect=_import_side_effect):
            _import_local_symbol("half_loaded", "X")

        # The stale entry should have been removed before the retry.
        self.assertFalse(
            captured_state.get("has_entry", True),
            "sys.modules should not contain 'half_loaded' during the retry import",
        )

        # Clean up.
        sys.modules.pop("half_loaded", None)

    def test_both_import_calls_use_same_module_name(self):
        """Both the initial attempt and the retry use the exact same module name."""
        fake_mod = _make_module("retry_mod", A=99)
        side_effects = [KeyError("retry_mod"), fake_mod]

        with patch("importlib.import_module", side_effect=side_effects) as mock_import:
            _import_local_symbol("retry_mod", "A")

        self.assertEqual(mock_import.call_args_list, [call("retry_mod"), call("retry_mod")])

    def test_only_one_retry_on_key_error(self):
        """The function retries exactly once; if the retry also raises KeyError, it propagates."""
        with patch("importlib.import_module", side_effect=KeyError("persistent")):
            with self.assertRaises(KeyError):
                _import_local_symbol("persistent_fail", "Anything")

    def test_key_error_on_retry_propagates(self):
        """A KeyError on the second attempt is not swallowed."""
        side_effects = [KeyError("first"), KeyError("second")]

        with patch("importlib.import_module", side_effect=side_effects):
            with self.assertRaises(KeyError):
                _import_local_symbol("double_fail_mod", "Symbol")


class TestImportLocalSymbolErrorPropagation(unittest.TestCase):
    """Non-KeyError exceptions must propagate without any retry."""

    def test_module_not_found_propagates_immediately(self):
        """ModuleNotFoundError is not a KeyError and must not trigger a retry."""
        with patch("importlib.import_module", side_effect=ModuleNotFoundError("nope")) as mock_import:
            with self.assertRaises(ModuleNotFoundError):
                _import_local_symbol("nonexistent_module", "Foo")

        # Only one call; no retry.
        mock_import.assert_called_once_with("nonexistent_module")

    def test_import_error_propagates_without_retry(self):
        """A generic ImportError is not retried."""
        with patch("importlib.import_module", side_effect=ImportError("bad")) as mock_import:
            with self.assertRaises(ImportError):
                _import_local_symbol("bad_mod", "Bar")

        mock_import.assert_called_once()

    def test_attribute_error_when_symbol_missing(self):
        """AttributeError is raised when the module exists but lacks the requested symbol."""
        fake_mod = _make_module("empty_mod")  # no attributes added

        with patch("importlib.import_module", return_value=fake_mod):
            with self.assertRaises(AttributeError):
                _import_local_symbol("empty_mod", "NonExistentSymbol")

    def test_attribute_error_after_successful_retry(self):
        """Even after a successful retry, AttributeError still propagates if symbol is absent."""
        fake_mod = _make_module("ok_mod_no_sym")
        side_effects = [KeyError("ok_mod_no_sym"), fake_mod]

        with patch("importlib.import_module", side_effect=side_effects):
            with self.assertRaises(AttributeError):
                _import_local_symbol("ok_mod_no_sym", "MissingAttr")

    def test_value_error_propagates_without_retry(self):
        """Arbitrary exceptions from import_module are not swallowed."""
        with patch("importlib.import_module", side_effect=ValueError("unexpected")) as mock_import:
            with self.assertRaises(ValueError):
                _import_local_symbol("some_mod", "SomeSym")

        mock_import.assert_called_once()


class TestImportLocalSymbolModuleLevelUsage(unittest.TestCase):
    """Regression: the four module-level _import_local_symbol calls in app.py resolve correctly."""

    def test_browser_automation_symbol_set(self):
        """app.BrowserAutomation is populated from _import_local_symbol at module load."""
        self.assertIsNotNone(app.BrowserAutomation)

    def test_mistral_client_symbol_set(self):
        """app.MistralClient is populated from _import_local_symbol at module load."""
        self.assertIsNotNone(app.MistralClient)

    def test_fireworks_client_symbol_set(self):
        """app.FireworksClient is populated from _import_local_symbol at module load."""
        self.assertIsNotNone(app.FireworksClient)

    def test_element_detector_symbol_set(self):
        """app.ElementDetector is populated from _import_local_symbol at module load."""
        self.assertIsNotNone(app.ElementDetector)


class TestImportLocalSymbolBoundaryAndRegression(unittest.TestCase):
    """Boundary conditions and extra regression coverage."""

    def test_symbol_with_leading_underscore(self):
        """Private symbols (leading underscore) are retrieved correctly."""
        fake_mod = _make_module("priv_mod", _internal=True)

        with patch("importlib.import_module", return_value=fake_mod):
            result = _import_local_symbol("priv_mod", "_internal")

        self.assertTrue(result)

    def test_deeply_nested_module_name(self):
        """Dotted (nested) module names are passed through unchanged."""
        fake_mod = _make_module("pkg.sub.leaf", Leaf="leaf_value")

        with patch("importlib.import_module", return_value=fake_mod) as mock_import:
            result = _import_local_symbol("pkg.sub.leaf", "Leaf")

        mock_import.assert_called_once_with("pkg.sub.leaf")
        self.assertEqual(result, "leaf_value")

    def test_sys_modules_not_modified_on_clean_import(self):
        """A successful first import must not alter sys.modules for that key."""
        fake_mod = _make_module("clean_mod", Val=7)

        # Ensure no pre-existing entry.
        sys.modules.pop("clean_mod", None)

        with patch("importlib.import_module", return_value=fake_mod):
            _import_local_symbol("clean_mod", "Val")

        # _import_local_symbol should not have touched sys.modules on success.
        self.assertNotIn("clean_mod", sys.modules)

    def test_key_error_clears_only_the_failing_module(self):
        """Only the module that raised KeyError is removed; other sys.modules entries survive."""
        unrelated_sentinel = object()
        sys.modules["unrelated_mod"] = unrelated_sentinel  # type: ignore[assignment]

        fake_mod = _make_module("target_mod", T=1)
        side_effects = [KeyError("target_mod"), fake_mod]

        with patch("importlib.import_module", side_effect=side_effects):
            _import_local_symbol("target_mod", "T")

        # The unrelated entry must be untouched.
        self.assertIs(sys.modules.get("unrelated_mod"), unrelated_sentinel)

        # Clean up.
        sys.modules.pop("unrelated_mod", None)

    def test_returns_none_when_attribute_is_none(self):
        """If the symbol exists but is explicitly None, the function returns None (not raises)."""
        fake_mod = _make_module("none_attr_mod", NullSymbol=None)

        with patch("importlib.import_module", return_value=fake_mod):
            result = _import_local_symbol("none_attr_mod", "NullSymbol")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
