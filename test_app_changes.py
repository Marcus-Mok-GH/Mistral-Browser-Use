"""
Tests for app.py changes introduced in this PR.

Changes covered:
- initialize_session_state: removed 'config_minimized' key
- delete_chat_screenshots: exception now silenced (no print)
- save_chats_to_local: exception now silenced (no print)
- load_chats_from_local: exception now silenced (no print), returns False
- setup_chat_menu: refactored to accept a container argument (not hardcoded to st.sidebar)
  and calls st.rerun() after state changes
"""
import inspect
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Stub all heavyweight top-level imports before importing app.py.
# This mirrors the pattern used in test_import_local_symbol.py.
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

# Provide realistic class stubs so module-level _import_local_symbol calls succeed.
sys.modules["browser_automation"].BrowserAutomation = MagicMock(name="BrowserAutomation")
sys.modules["mistral_client"].MistralClient = MagicMock(name="MistralClient")
sys.modules["fireworks_client"].FireworksClient = MagicMock(name="FireworksClient")
sys.modules["element_detector"].ElementDetector = MagicMock(name="ElementDetector")

# Give streamlit a usable session_state.
import streamlit as st  # noqa: E402
st.session_state = {}  # type: ignore[assignment]

import app  # noqa: E402
from app import (  # noqa: E402
    initialize_session_state,
    delete_chat_screenshots,
    save_chats_to_local,
    load_chats_from_local,
    setup_chat_menu,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_session_state():
    """Clear all session state between tests."""
    st.session_state.clear()


# ---------------------------------------------------------------------------
# initialize_session_state – config_minimized removed
# ---------------------------------------------------------------------------

class TestInitializeSessionState(unittest.TestCase):
    """Verify that initialize_session_state no longer sets config_minimized."""

    def setUp(self):
        _reset_session_state()
        # LocalStorage mock so initialization doesn't blow up
        sys.modules["streamlit_local_storage"].LocalStorage.return_value = MagicMock()

    def test_config_minimized_not_set(self):
        """config_minimized must NOT be present in session_state after initialization."""
        initialize_session_state()
        self.assertNotIn(
            "config_minimized",
            st.session_state,
            "config_minimized was removed in this PR and must not be initialised",
        )

    def test_messages_initialised(self):
        """'messages' is still initialised to an empty list."""
        initialize_session_state()
        self.assertIn("messages", st.session_state)
        self.assertEqual(st.session_state["messages"], [])

    def test_todos_initialised(self):
        """'todos' is still initialised to an empty list."""
        initialize_session_state()
        self.assertIn("todos", st.session_state)

    def test_chats_initialised(self):
        """'chats' is still initialised to an empty dict."""
        initialize_session_state()
        self.assertIn("chats", st.session_state)
        self.assertEqual(st.session_state["chats"], {})

    def test_usage_data_initialised(self):
        """'usage_data' is still initialised with count=0."""
        initialize_session_state()
        self.assertIn("usage_data", st.session_state)
        self.assertEqual(st.session_state["usage_data"]["count"], 0)

    def test_existing_keys_not_overwritten(self):
        """Pre-existing session state values are not overwritten."""
        st.session_state["messages"] = ["existing"]
        initialize_session_state()
        self.assertEqual(st.session_state["messages"], ["existing"])

    def test_idempotent_call(self):
        """Calling initialize_session_state twice is safe and does not change state."""
        initialize_session_state()
        first_chats = dict(st.session_state["chats"])
        initialize_session_state()
        self.assertEqual(st.session_state["chats"], first_chats)


# ---------------------------------------------------------------------------
# delete_chat_screenshots – exception silenced (no print)
# ---------------------------------------------------------------------------

class TestDeleteChatScreenshots(unittest.TestCase):
    """Verify that delete_chat_screenshots silences exceptions without printing."""

    def setUp(self):
        _reset_session_state()

    def _setup_chat_with_images(self, paths):
        chat_id = "chat_1"
        st.session_state["chats"] = {
            chat_id: {
                "messages": [
                    {"type": "image", "content": p} for p in paths
                ]
            }
        }
        return chat_id

    def test_deletes_existing_image_files(self):
        """Removes screenshot files that exist on disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "shot.png")
            open(img_path, "wb").close()
            chat_id = self._setup_chat_with_images([img_path])
            delete_chat_screenshots(chat_id)
            self.assertFalse(os.path.exists(img_path))

    def test_silences_os_remove_exception(self):
        """Does not raise (and does not print) when os.remove fails."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "shot.png")
            open(img_path, "wb").close()
            chat_id = self._setup_chat_with_images([img_path])
            with patch("os.remove", side_effect=PermissionError("denied")):
                # Must not raise
                delete_chat_screenshots(chat_id)

    def test_no_print_on_os_remove_exception(self):
        """No output is printed when os.remove raises."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "shot.png")
            open(img_path, "wb").close()
            chat_id = self._setup_chat_with_images([img_path])
            with patch("os.remove", side_effect=OSError("denied")), \
                 patch("builtins.print") as mock_print:
                delete_chat_screenshots(chat_id)
            mock_print.assert_not_called()

    def test_skips_non_existent_files(self):
        """Does not call os.remove for files that do not exist."""
        chat_id = self._setup_chat_with_images(["/nonexistent/shot.png"])
        with patch("os.remove") as mock_rm:
            delete_chat_screenshots(chat_id)
        mock_rm.assert_not_called()

    def test_skips_non_image_messages(self):
        """Only messages with type='image' are considered."""
        chat_id = "chat_2"
        st.session_state["chats"] = {
            chat_id: {
                "messages": [
                    {"type": "text", "content": "/some/file.txt"},
                ]
            }
        }
        with patch("os.remove") as mock_rm:
            delete_chat_screenshots(chat_id)
        mock_rm.assert_not_called()

    def test_does_nothing_for_unknown_chat_id(self):
        """Safely ignores a chat_id that is not in session_state.chats."""
        st.session_state["chats"] = {}
        delete_chat_screenshots("nonexistent_id")  # must not raise

    def test_handles_multiple_images(self):
        """All image files for a chat are deleted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = [os.path.join(tmp_dir, f"shot_{i}.png") for i in range(3)]
            for p in paths:
                open(p, "wb").close()
            chat_id = self._setup_chat_with_images(paths)
            delete_chat_screenshots(chat_id)
            for p in paths:
                self.assertFalse(os.path.exists(p))


# ---------------------------------------------------------------------------
# save_chats_to_local – exception silenced (no print)
# ---------------------------------------------------------------------------

class TestSaveChatsToLocal(unittest.TestCase):
    """Verify that save_chats_to_local silences exceptions without printing."""

    def setUp(self):
        _reset_session_state()
        mock_storage = MagicMock()
        st.session_state["chats"] = {}
        st.session_state["usage_data"] = {"count": 0, "reset_date": "2030-01-01"}
        st.session_state["local_storage"] = mock_storage

    def test_calls_setitem_for_chats(self):
        """setItem is called with 'mbu_chats' key."""
        st.session_state["chats"] = {
            "c1": {"title": "Test", "messages": [], "todos": []}
        }
        save_chats_to_local()
        calls = [c[0][0] for c in st.session_state["local_storage"].setItem.call_args_list]
        self.assertIn("mbu_chats", calls)

    def test_calls_setitem_for_usage(self):
        """setItem is called with 'mbu_usage' key."""
        save_chats_to_local()
        calls = [c[0][0] for c in st.session_state["local_storage"].setItem.call_args_list]
        self.assertIn("mbu_usage", calls)

    def test_silences_exception_from_local_storage(self):
        """Does not raise when local_storage.setItem raises."""
        st.session_state["local_storage"].setItem.side_effect = RuntimeError("storage full")
        save_chats_to_local()  # must not raise

    def test_no_print_on_exception(self):
        """No output is printed when an exception occurs."""
        st.session_state["local_storage"].setItem.side_effect = RuntimeError("fail")
        with patch("builtins.print") as mock_print:
            save_chats_to_local()
        mock_print.assert_not_called()

    def test_serialises_chat_metadata_only(self):
        """Only title, messages, and todos are included in the serialised chats."""
        st.session_state["chats"] = {
            "c1": {
                "title": "My Chat",
                "messages": [{"type": "text", "content": "hello"}],
                "todos": ["item1"],
                "extra_field": "should_be_ignored",  # not in serialisable
            }
        }
        save_chats_to_local()
        # Grab the JSON passed to setItem("mbu_chats", ...)
        for c in st.session_state["local_storage"].setItem.call_args_list:
            if c[0][0] == "mbu_chats":
                parsed = json.loads(c[0][1])
                self.assertIn("c1", parsed)
                self.assertEqual(parsed["c1"]["title"], "My Chat")
                self.assertNotIn("extra_field", parsed["c1"])
                break


# ---------------------------------------------------------------------------
# load_chats_from_local – exception silenced (no print), returns False
# ---------------------------------------------------------------------------

class TestLoadChatsFromLocal(unittest.TestCase):
    """Verify that load_chats_from_local silences exceptions and returns False."""

    def setUp(self):
        _reset_session_state()
        mock_storage = MagicMock()
        st.session_state["local_storage"] = mock_storage
        st.session_state["chats"] = {}
        st.session_state["usage_data"] = {"count": 0, "reset_date": "2030-01-01"}

    def test_returns_false_when_no_chats_stored(self):
        """Returns False when local_storage has no chats data."""
        st.session_state["local_storage"].getItem.return_value = None
        result = load_chats_from_local()
        self.assertFalse(result)

    def test_returns_true_when_chats_stored(self):
        """Returns True when chats are loaded successfully from local_storage."""
        stored = json.dumps({"c1": {"title": "T", "messages": [], "todos": []}})

        def _get_item(key):
            if key == "mbu_chats":
                return stored
            return None

        st.session_state["local_storage"].getItem.side_effect = _get_item
        result = load_chats_from_local()
        self.assertTrue(result)

    def test_loads_chats_into_session_state(self):
        """session_state.chats is populated from local_storage on success."""
        stored = json.dumps({"c1": {"title": "Chat", "messages": [], "todos": []}})

        def _get_item(key):
            if key == "mbu_chats":
                return stored
            return None

        st.session_state["local_storage"].getItem.side_effect = _get_item
        load_chats_from_local()
        self.assertIn("c1", st.session_state["chats"])

    def test_returns_false_on_exception(self):
        """Returns False (does not raise) when local_storage raises."""
        st.session_state["local_storage"].getItem.side_effect = RuntimeError("broken")
        result = load_chats_from_local()
        self.assertFalse(result)

    def test_no_print_on_exception(self):
        """No output is printed when an exception occurs."""
        st.session_state["local_storage"].getItem.side_effect = RuntimeError("broken")
        with patch("builtins.print") as mock_print:
            load_chats_from_local()
        mock_print.assert_not_called()

    def test_returns_false_on_invalid_json(self):
        """Returns False when stored data is not valid JSON."""
        def _get_item(key):
            if key == "mbu_chats":
                return "{ bad json }"
            return None

        st.session_state["local_storage"].getItem.side_effect = _get_item
        result = load_chats_from_local()
        self.assertFalse(result)

    def test_no_print_on_invalid_json(self):
        """No output is printed when JSON parsing fails."""
        st.session_state["local_storage"].getItem.return_value = "not json"
        with patch("builtins.print") as mock_print:
            load_chats_from_local()
        mock_print.assert_not_called()


# ---------------------------------------------------------------------------
# setup_chat_menu – signature change: accepts container argument
# ---------------------------------------------------------------------------

class TestSetupChatMenuSignature(unittest.TestCase):
    """Verify setup_chat_menu was refactored to accept a container argument."""

    def test_accepts_container_argument(self):
        """setup_chat_menu must accept a positional 'container' parameter."""
        sig = inspect.signature(setup_chat_menu)
        params = list(sig.parameters.keys())
        self.assertIn("container", params)

    def test_container_is_first_positional_parameter(self):
        """'container' is the first (and expected to be only required) parameter."""
        sig = inspect.signature(setup_chat_menu)
        first_param = list(sig.parameters.keys())[0]
        self.assertEqual(first_param, "container")

    def test_calls_container_button_for_new_chat(self):
        """setup_chat_menu calls container.button, not st.sidebar.button."""
        _reset_session_state()
        st.session_state["chats"] = {}
        st.session_state["current_chat_id"] = None

        mock_container = MagicMock()
        # Simulate the "New Chat" button NOT being clicked (returns False)
        mock_container.button.return_value = False
        mock_container.columns.return_value = (MagicMock(), MagicMock())

        setup_chat_menu(mock_container)

        mock_container.button.assert_called()
        # Verify the first button call is for "New Chat"
        first_call_args = mock_container.button.call_args_list[0]
        self.assertIn("New Chat", first_call_args[0][0])

    def test_calls_container_divider(self):
        """setup_chat_menu calls container.divider() (not st.sidebar.divider)."""
        _reset_session_state()
        st.session_state["chats"] = {}
        st.session_state["current_chat_id"] = None

        mock_container = MagicMock()
        mock_container.button.return_value = False
        mock_container.columns.return_value = (MagicMock(), MagicMock())

        setup_chat_menu(mock_container)

        mock_container.divider.assert_called_once()

    def test_calls_st_rerun_when_new_chat_clicked(self):
        """st.rerun() is called when the New Chat button is clicked."""
        _reset_session_state()
        st.session_state["chats"] = {}
        st.session_state["current_chat_id"] = None
        st.session_state["messages"] = []

        mock_container = MagicMock()
        # First button call = "New Chat" → clicked (True)
        mock_container.button.side_effect = [True]
        mock_container.columns.return_value = (MagicMock(), MagicMock())

        with patch.object(st, "rerun") as mock_rerun, \
             patch("app.save_chats_to_local"):
            setup_chat_menu(mock_container)

        mock_rerun.assert_called()

    def test_creates_new_chat_in_session_state(self):
        """Clicking New Chat adds an entry to st.session_state.chats."""
        _reset_session_state()
        st.session_state["chats"] = {}
        st.session_state["current_chat_id"] = None
        st.session_state["messages"] = []

        mock_container = MagicMock()
        mock_container.button.side_effect = [True]
        mock_container.columns.return_value = (MagicMock(), MagicMock())

        with patch.object(st, "rerun"), patch("app.save_chats_to_local"):
            setup_chat_menu(mock_container)

        self.assertEqual(len(st.session_state["chats"]), 1)
        chat = list(st.session_state["chats"].values())[0]
        self.assertEqual(chat["title"], "New Chat")

    def test_calls_container_columns_for_each_chat(self):
        """container.columns is called once per existing chat."""
        _reset_session_state()
        st.session_state["chats"] = {
            "c1": {"title": "Chat 1", "messages": [], "todos": []},
            "c2": {"title": "Chat 2", "messages": [], "todos": []},
        }
        st.session_state["current_chat_id"] = "c1"

        mock_container = MagicMock()
        mock_container.button.return_value = False
        col_chat = MagicMock()
        col_del = MagicMock()
        col_chat.button.return_value = False
        col_del.button.return_value = False
        mock_container.columns.return_value = (col_chat, col_del)

        setup_chat_menu(mock_container)

        self.assertEqual(mock_container.columns.call_count, 2)


if __name__ == "__main__":
    unittest.main()