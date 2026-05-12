import streamlit as st
import os
import time
import base64
from datetime import datetime, timedelta
from browser_automation import BrowserAutomation
from mistral_client import MistralClient
from fireworks_client import FireworksClient
from element_detector import ElementDetector
import traceback
import extra_streamlit_components as stx
from streamlit_local_storage import LocalStorage
import uuid
import json

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'todos' not in st.session_state:
        st.session_state.todos = []
    if 'browser' not in st.session_state:
        st.session_state.browser = None
    if 'ai_client' not in st.session_state:
        st.session_state.ai_client = None
    if 'ai_provider' not in st.session_state:
        st.session_state.ai_provider = "Mistral"
    if 'element_detector' not in st.session_state:
        st.session_state.element_detector = ElementDetector()
    if 'automation_active' not in st.session_state:
        st.session_state.automation_active = False
    if 'current_objective' not in st.session_state:
        st.session_state.current_objective = None
    if 'mistral_api_key' not in st.session_state:
        st.session_state.mistral_api_key = ""
    if 'firecrawl_api_key' not in st.session_state:
        st.session_state.firecrawl_api_key = ""
    if 'chats' not in st.session_state:
        st.session_state.chats = {}
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    if 'local_storage' not in st.session_state:
        st.session_state.local_storage = LocalStorage()
    if 'config_minimized' not in st.session_state:
        st.session_state.config_minimized = False
    if 'usage_data' not in st.session_state:
        st.session_state.usage_data = {
            'count': 0,
            'reset_date': (datetime.now() + timedelta(days=7)).isoformat()
        }

def delete_chat_screenshots(chat_id):
    """Delete all screenshots associated with a chat"""
    if chat_id in st.session_state.chats:
        messages = st.session_state.chats[chat_id].get('messages', [])
        for msg in messages:
            if msg.get('type') == 'image' and os.path.exists(msg.get('content')):
                try:
                    os.remove(msg.get('content'))
                except Exception as e:
                    print(f"Error deleting screenshot {msg.get('content')}: {e}")

def save_chats_to_local():
    """Save all chats and usage data to localStorage"""
    try:
        # We only save metadata and messages, not the whole session state
        serializable_chats = {}
        for cid, chat in st.session_state.chats.items():
            serializable_chats[cid] = {
                'title': chat.get('title', 'Untitled Chat'),
                'messages': chat.get('messages', []),
                'todos': chat.get('todos', [])
            }
        st.session_state.local_storage.setItem("mbu_chats", json.dumps(serializable_chats, default=str))

        # Save usage data
        st.session_state.local_storage.setItem("mbu_usage", json.dumps(st.session_state.usage_data, default=str))
    except Exception as e:
        print(f"Error saving to localStorage: {e}")

def load_chats_from_local():
    """Load all chats and usage data from localStorage"""
    try:
        # Load usage data
        stored_usage = st.session_state.local_storage.getItem("mbu_usage")
        if stored_usage:
            st.session_state.usage_data = json.loads(stored_usage)
            # Check for weekly reset
            reset_date = datetime.fromisoformat(st.session_state.usage_data.get('reset_date'))
            if datetime.now() > reset_date:
                st.session_state.usage_data = {
                    'count': 0,
                    'reset_date': (datetime.now() + timedelta(days=7)).isoformat()
                }

        stored_chats = st.session_state.local_storage.getItem("mbu_chats")
        if stored_chats:
            st.session_state.chats = json.loads(stored_chats)
            return True
    except Exception as e:
        print(f"Error loading from localStorage: {e}")
    return False

def setup_chat_menu():
    """Setup left sidebar for chat management"""
    st.sidebar.title("💬 Chats")
    
    if st.sidebar.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chats[new_id] = {
            'title': 'New Chat',
            'messages': [],
            'todos': []
        }
        st.session_state.current_chat_id = new_id
        st.session_state.messages = []
        save_chats_to_local()

    st.sidebar.divider()

    # List existing chats
    for cid, chat in list(st.session_state.chats.items()):
        col_chat, col_del = st.sidebar.columns([0.8, 0.2])

        # Highlight current chat
        is_current = (cid == st.session_state.current_chat_id)
        chat_title = chat.get('title', 'Untitled Chat')
        if is_current:
            chat_title = f"👉 {chat_title}"

        if col_chat.button(chat_title, key=f"btn_{cid}", use_container_width=True):
            st.session_state.current_chat_id = cid
            st.session_state.messages = chat.get('messages', [])
            st.session_state.todos = chat.get('todos', [])

        if col_del.button("🗑️", key=f"del_{cid}"):
            delete_chat_screenshots(cid)
            del st.session_state.chats[cid]
            if st.session_state.current_chat_id == cid:
                st.session_state.current_chat_id = None
                st.session_state.messages = []
                st.session_state.todos = []
            save_chats_to_local()

def setup_configuration_panel(container):
    """Setup right configuration panel with improved spacing and organization"""
    # Title is now handled in the main layout for better control with the minimize button
    
    cookie_manager = stx.CookieManager()

    cookies = cookie_manager.get_all()
    # Wait for cookies to load
    if cookies is None:
        return

    # Load settings from cookies if session state is empty
    if not st.session_state.mistral_api_key:
        st.session_state.mistral_api_key = cookies.get("mistral_api_key") or ""
    if not st.session_state.firecrawl_api_key:
        st.session_state.firecrawl_api_key = cookies.get("firecrawl_api_key") or ""

    saved_provider = cookies.get("ai_provider")
    if saved_provider and st.session_state.ai_provider != saved_provider:
         st.session_state.ai_provider = saved_provider

    # Use tabs to reduce vertical "crowdedness"
    tab_provider, tab_browser = container.tabs(["🤖 Provider", "🌐 Browser"])

    with tab_provider:
        st.subheader("AI Provider")
        providers = ["Mistral", "Fireworks"]
        current_provider_index = providers.index(st.session_state.ai_provider) if st.session_state.ai_provider in providers else 0

        selected_provider = st.selectbox(
            "Select Provider",
            options=providers,
            index=current_provider_index,
            key="provider_select"
        )

        if selected_provider != st.session_state.ai_provider:
            st.session_state.ai_provider = selected_provider
            cookie_manager.set("ai_provider", selected_provider, expires_at=datetime.now() + timedelta(days=10))
            st.session_state.ai_client = None # Reset client to force re-init
            st.rerun()

        if st.session_state.ai_provider == "Mistral":
            st.subheader("Mistral AI API Key")
            mistral_api_key = st.text_input(
                "Mistral API Key",
                value=st.session_state.mistral_api_key,
                type="password",
                help="Enter your Mistral AI API key",
                key="mistral_input"
            )

            if mistral_api_key != st.session_state.mistral_api_key:
                cookie_manager.set("mistral_api_key", mistral_api_key, expires_at=datetime.now() + timedelta(days=10))
                st.session_state.mistral_api_key = mistral_api_key
                if mistral_api_key:
                    st.session_state.ai_client = MistralClient(mistral_api_key)
                else:
                    st.session_state.ai_client = None

            if st.session_state.mistral_api_key:
                if st.session_state.ai_client is None or not isinstance(st.session_state.ai_client, MistralClient):
                    try:
                        st.session_state.ai_client = MistralClient(st.session_state.mistral_api_key)
                    except Exception as e:
                        st.error(f"Error initializing Mistral client: {e}")
                st.success("✅ Mistral API Key configured")
            else:
                st.warning("⚠️ Please enter your Mistral AI API key")

        elif st.session_state.ai_provider == "Fireworks":
            if st.session_state.ai_client is None or not isinstance(st.session_state.ai_client, FireworksClient):
                st.session_state.ai_client = FireworksClient()
            st.success(f"✅ Fireworks configured (Model: {st.session_state.ai_client.model})")

        st.divider()

        st.subheader("Firecrawl API Key")
        firecrawl_api_key = st.text_input(
            "Firecrawl API Key",
            value=st.session_state.firecrawl_api_key,
            type="password",
            help="Enter your Firecrawl API key",
            key="firecrawl_input"
        )

        if firecrawl_api_key != st.session_state.firecrawl_api_key:
            cookie_manager.set("firecrawl_api_key", firecrawl_api_key, expires_at=datetime.now() + timedelta(days=10))
            st.session_state.firecrawl_api_key = firecrawl_api_key
            if st.session_state.browser:
                st.session_state.browser.close()
                st.session_state.browser = None

        if st.session_state.firecrawl_api_key:
            st.success("✅ Firecrawl API Key configured")
        else:
            st.warning("⚠️ Please enter your Firecrawl API key")
    
    with tab_browser:
        # Browser Controls
        st.subheader("Browser Controls")

        if st.button("🚀 Start Browser", disabled=st.session_state.automation_active, use_container_width=True):
            try:
                if not st.session_state.firecrawl_api_key:
                    st.error("❌ Firecrawl API Key is required")
                else:
                    st.session_state.browser = BrowserAutomation(api_key=st.session_state.firecrawl_api_key)
                    st.session_state.browser.start_browser()
                    st.success("✅ Browser started")
            except Exception as e:
                st.error(f"❌ Failed to start browser: {str(e)}")

        if st.button("🛑 Stop Browser", disabled=not st.session_state.automation_active, use_container_width=True):
            try:
                if st.session_state.browser:
                    st.session_state.browser.close()
                    st.session_state.browser = None
                    st.session_state.automation_active = False
                st.success("✅ Browser stopped")
            except Exception as e:
                st.error(f"❌ Failed to stop browser: {str(e)}")

        # Status indicators
        st.divider()
        st.subheader("Current Status")

        browser_status = "🟢 Running" if st.session_state.browser and st.session_state.automation_active else "🔴 Stopped"
        st.write(f"Browser: {browser_status}")

        api_status = "🟢 Connected" if st.session_state.ai_client else "🔴 Not configured"
        st.write(f"{st.session_state.ai_provider}: {api_status}")

def display_chat_history():
    """Display chat message history"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["type"] == "text":
                st.write(message["content"])
            elif message["type"] == "image":
                # Only try to display if file exists and is not empty
                img_path = message["content"]
                if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                    try:
                        st.image(img_path, caption=message.get("caption", "Screenshot"))
                    except Exception as e:
                        st.error(f"Error displaying image: {e}")
                else:
                    st.warning(f"Image not found or empty: {img_path}")
            elif message["type"] == "thinking":
                st.info(f"🤔 **Thinking:** {message['content']}")
            elif message["type"] == "action":
                st.success(f"⚡ **Action:** {message['content']}")
            elif message["type"] == "error":
                st.error(f"❌ **Error:** {message['content']}")

def add_message(role, content, msg_type="text", caption=None):
    """Add a message to chat history"""
    message = {
        "role": role,
        "type": msg_type,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    if caption:
        message["caption"] = caption
    st.session_state.messages.append(message)

    # Update current chat in session state and local storage
    if st.session_state.current_chat_id:
        st.session_state.chats[st.session_state.current_chat_id]['messages'] = st.session_state.messages
        save_chats_to_local()

def take_screenshot_and_analyze():
    """Take screenshot and analyze with element detection"""
    try:
        if not st.session_state.browser:
            raise Exception("Browser not started")
        
        # Take screenshot
        screenshot_path = st.session_state.browser.take_screenshot()
        add_message("assistant", screenshot_path, "image", "Current page screenshot")
        
        # Detect and highlight elements
        annotated_image_path = st.session_state.element_detector.detect_and_annotate_elements(screenshot_path, st.session_state.browser)
        add_message("assistant", annotated_image_path, "image", "Elements detected and indexed")
        
        return annotated_image_path
        
    except Exception as e:
        error_msg = f"Failed to take screenshot: {str(e)}"
        add_message("assistant", error_msg, "error")
        return None

def execute_automation_step(user_objective):
    """Execute one step of the automation process"""
    try:
        if not st.session_state.ai_client:
            raise Exception(f"{st.session_state.ai_provider} AI client not configured")
        
        if not st.session_state.browser:
            raise Exception("Browser not started")
        
        # Take screenshot and analyze
        annotated_image_path = take_screenshot_and_analyze()
        if not annotated_image_path:
            return False
        
        # Get AI reasoning and action
        with open(annotated_image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Get image format from extension
        _, extension = os.path.splitext(annotated_image_path)
        image_format = extension.strip('.').lower()
        if image_format == 'jpg': image_format = 'jpeg'

        # Increment usage count for the analysis request
        st.session_state.usage_data['count'] += 1
        save_chats_to_local()

        response = st.session_state.ai_client.analyze_and_decide(
            image_data, user_objective, st.session_state.current_objective, image_format=image_format, todos=st.session_state.todos
        )
        
        # Parse response
        thinking = response.get('thinking', 'No reasoning provided')
        action = response.get('action', 'No action specified')
        
        add_message("assistant", thinking, "thinking")
        add_message("assistant", action, "action")
        
        # Execute action
        import re
        if action.lower().startswith('click('):
            # Extract index from click(INDEX)
            index_str = action.split('(')[1].split(')')[0]
            try:
                index = int(index_str)
                st.session_state.browser.click_element_by_index(index)
                add_message("assistant", f"Clicked element at index {index}")
            except ValueError:
                raise Exception(f"Invalid index in action: {action}")
        
        elif action.lower().startswith('type('):
            # Extract text and element from type("TEXT", into="ELEMENT") or type('TEXT', into='ELEMENT')
            # Match both single and double quotes
            match = re.search(r"type\(['\"](.*?)['\"]\s*,\s*into\s*=\s*['\"](.*?)['\"]\)", action)
            if match:
                text = match.group(1)
                element = match.group(2)
                st.session_state.browser.type_text(text, element)
                add_message("assistant", f"Typed '{text}' into {element}")
            else:
                raise Exception(f"Invalid type action format: {action}")
        
        elif action.lower().startswith('todo_add('):
            match = re.search(r"todo_add\(['\"](.*?)['\"]\)", action)
            if match:
                task = match.group(1)
                st.session_state.todos.append(task)
                if st.session_state.current_chat_id:
                    st.session_state.chats[st.session_state.current_chat_id]['todos'] = st.session_state.todos
                    save_chats_to_local()
                add_message("assistant", f"Added to-do: {task}")
            else:
                raise Exception(f"Invalid todo_add action format: {action}")

        elif action.lower().startswith('todo_edit('):
            match = re.search(r"todo_edit\((\d+)\s*,\s*['\"](.*?)['\"]\)", action)
            if match:
                idx = int(match.group(1))
                task = match.group(2)
                if 0 <= idx < len(st.session_state.todos):
                    st.session_state.todos[idx] = task
                    if st.session_state.current_chat_id:
                        st.session_state.chats[st.session_state.current_chat_id]['todos'] = st.session_state.todos
                        save_chats_to_local()
                    add_message("assistant", f"Updated to-do at index {idx}: {task}")
                else:
                    raise Exception(f"Todo index {idx} out of range")
            else:
                raise Exception(f"Invalid todo_edit action format: {action}")

        elif action.lower().startswith('todo_delete('):
            match = re.search(r"todo_delete\((\d+)\)", action)
            if match:
                idx = int(match.group(1))
                if 0 <= idx < len(st.session_state.todos):
                    removed = st.session_state.todos.pop(idx)
                    if st.session_state.current_chat_id:
                        st.session_state.chats[st.session_state.current_chat_id]['todos'] = st.session_state.todos
                        save_chats_to_local()
                    add_message("assistant", f"Deleted to-do: {removed}")
                else:
                    raise Exception(f"Todo index {idx} out of range")
            else:
                raise Exception(f"Invalid todo_delete action format: {action}")

        elif 'complete' in action.lower() or 'done' in action.lower():
            st.session_state.automation_active = False
            add_message("assistant", "🎉 Objective completed successfully!")
            return False
        
        else:
            add_message("assistant", f"Unknown action: {action}", "error")
        
        return True
        
    except Exception as e:
        error_msg = f"Automation step failed: {str(e)}\n{traceback.format_exc()}"
        add_message("assistant", error_msg, "error")
        st.session_state.automation_active = False
        return False

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Web Automation Assistant",
        page_icon="🤖",
        layout="wide"
    )
    
    initialize_session_state()
    user_input = None
    
    # Load chats from local storage if session state is empty
    if not st.session_state.chats:
        if load_chats_from_local():
            # Set current chat if none selected
            if not st.session_state.current_chat_id and st.session_state.chats:
                st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
                current_chat = st.session_state.chats[st.session_state.current_chat_id]
                st.session_state.messages = current_chat.get('messages', [])
                st.session_state.todos = current_chat.get('todos', [])

    setup_chat_menu()

    # Layout: adjusted ratios for a wider config panel when expanded
    if st.session_state.config_minimized:
        col_main, col_config = st.columns([10, 1])
    else:
        # Wider configuration panel (e.g., [2, 1] instead of [3, 1])
        col_main, col_config = st.columns([2, 1])
    
    with col_main:
        st.title("🤖 Web Automation Assistant")
        st.subheader("Powered by Mistral AI & Computer Vision")

        if not st.session_state.current_chat_id:
            st.info("👈 Please start a new chat or select an existing one from the menu.")
        else:
            # Main chat interface
            st.write(f"Objective: **{st.session_state.chats[st.session_state.current_chat_id].get('title')}**")

            # Display Todo List if it exists
            if st.session_state.todos:
                with st.expander("📝 Todo List", expanded=True):
                    for i, todo in enumerate(st.session_state.todos):
                        st.write(f"{i}. {todo}")

            # Display chat history
            display_chat_history()

            # User input
            user_input = st.chat_input("What would you like me to do on the web?")

            # Display usage and promo code at the bottom middle
            st.divider()
            usage_col1, usage_col2, usage_col3 = st.columns([1, 2, 1])
            with usage_col2:
                count = st.session_state.usage_data.get('count', 0)
                st.markdown(f"<p style='text-align: center; color: gray;'>Requests this week: <b>{count} / 20</b></p>", unsafe_allow_html=True)

                promo_code = st.text_input(
                    "Renewal Code",
                    placeholder="Enter code to reset limit",
                    label_visibility="collapsed",
                    key="promo_input"
                )

                if promo_code == "2026CODERENEWAL":
                    st.session_state.usage_data['count'] = 0
                    save_chats_to_local()
                    st.success("✅ Limit reset successfully!")
                    st.session_state.promo_input = ""
                    time.sleep(1)
                    st.rerun()
                elif promo_code:
                    st.error("❌ Invalid code")
    
    with col_config:
        if st.session_state.config_minimized:
            # Expand button when minimized
            st.button("<", help="Expand Configuration", key="expand_btn", on_click=lambda: st.session_state.update({"config_minimized": False}))
        else:
            # Layout for Minimize button and Title
            # Adjusted ratio to give the button more space and prevent title wrapping
            top_col1, top_col2 = st.columns([0.25, 0.75])
            with top_col1:
                st.button(">", help="Minimize Configuration", key="minimize_btn", on_click=lambda: st.session_state.update({"config_minimized": True}))
            with top_col2:
                # Removed redundant icon to save horizontal space
                st.markdown("### Configuration")

            setup_configuration_panel(st.container())
    
    if user_input:
        add_message("user", user_input)

        # Check request limit
        if st.session_state.usage_data.get('count', 0) >= 20:
            add_message("assistant", "⚠️ You have reached your weekly limit of 20 requests. Please enter a renewal code to continue.", "error")
            st.rerun()
            return
        
        # Check prerequisites
        if not st.session_state.ai_client:
            add_message("assistant", f"Please configure your {st.session_state.ai_provider} AI settings in the sidebar first.", "error")
            st.rerun()
            return
        
        if not st.session_state.browser:
            add_message("assistant", "Please start the browser first using the sidebar controls.", "error")
            st.rerun()
            return
        
        # Start automation
        st.session_state.current_objective = user_input
        st.session_state.automation_active = True
        
        # Automatically name chat if it's the first message
        if len(st.session_state.messages) <= 1:
            if st.session_state.ai_client:
                with st.spinner("Generating chat title..."):
                    # Increment usage for title generation too
                    st.session_state.usage_data['count'] += 1
                    save_chats_to_local()

                    title = st.session_state.ai_client.generate_chat_title(user_input)
                    st.session_state.chats[st.session_state.current_chat_id]['title'] = title
                    save_chats_to_local()

        add_message("assistant", f"Starting automation for: {user_input}")
        
        # Execute automation steps
        max_steps = 20  # Prevent infinite loops
        step_count = 0
        
        while st.session_state.automation_active and step_count < max_steps:
            step_count += 1
            add_message("assistant", f"--- Step {step_count} ---")
            
            success = execute_automation_step(user_input)
            if not success:
                break
            
            time.sleep(2)  # Brief pause between steps
        
        if step_count >= max_steps:
            add_message("assistant", "Maximum steps reached. Stopping automation.", "error")
            st.session_state.automation_active = False
        
        st.rerun()
    
    # Auto-continue automation if active
    if st.session_state.automation_active:
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    main()
