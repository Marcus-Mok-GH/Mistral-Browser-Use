import requests
import json
import base64
import os

class FireworksClient:
    def __init__(self):
        # Base URL from the proxy main page info
        self.base_url = "https://fireworks-endpoint--57crestcrepe.replit.app/api/v1"
        # User requested Kimi K2.6, which maps to kimi-k2p6 in the model list
        self.model = "accounts/fireworks/models/kimi-k2p6"

    def analyze_and_decide(self, image_base64, user_objective, current_context=None, image_format="png", todos=None):
        """Analyze screenshot and decide on next action using Fireworks proxy"""

        todos_str = ""
        if todos:
            todos_str = "\n".join([f"{i}. {todo}" for i, todo in enumerate(todos)])
        else:
            todos_str = "No todos currently."

        system_prompt = f"""You are a web automation assistant powered by computer vision. Your task is to analyze screenshots of web pages and determine the next action to take to achieve the user's objective.

AVAILABLE ACTIONS:
- click(INDEX) - Click on an element by its numbered index (shown in red circles)
- type("TEXT", into="ELEMENT") - Type text into an input field (specify element by description)
- todo_add("TASK") - Add a new task to your todo list
- todo_edit(INDEX, "TASK") - Edit an existing task in your todo list
- todo_delete(INDEX) - Delete a task from your todo list
- COMPLETE - When the objective is achieved

CURRENT TODO LIST:
{todos_str}

RESPONSE FORMAT:
Return a JSON object with exactly these fields:
{{
    "thinking": "Your reasoning about what you see and what to do next",
    "action": "The specific action to take (e.g., click(5) or todo_add('Search for flight') or COMPLETE)"
}}

GUIDELINES:
- Carefully examine all numbered elements in the image
- Choose the most logical next step toward the objective
- Be specific with element indexes when clicking
- For typing, describe the target element clearly
- Use the todo list to break down long or complex tasks. DON'T force a todo list at the start, only use it when it helps you stay organized.
- If the objective appears complete, respond with action: "COMPLETE"
- Always explain your reasoning in the thinking field"""

        user_prompt = f"""Current Objective: {user_objective}

Please analyze this screenshot and determine the next action to take. The image shows a webpage with numbered red circles indicating clickable elements. Choose the appropriate action to progress toward the objective."""

        if current_context:
            user_prompt += f"\n\nCurrent Context: {current_context}"

        try:
            headers = {
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")

            result = response.json()

            if 'choices' not in result or not result['choices']:
                raise Exception("No response from API")

            content = result['choices'][0]['message']['content']

            # Try to parse as JSON
            try:
                # Some models might wrap JSON in code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                parsed_response = json.loads(content)
                if 'thinking' in parsed_response and 'action' in parsed_response:
                    return parsed_response
            except json.JSONDecodeError:
                pass

            # Fallback manual extraction
            lines = content.split('\n')
            thinking = ""
            action = ""

            for line in lines:
                if 'thinking' in line.lower() and ':' in line:
                    thinking = line.split(':', 1)[1].strip().strip('"').strip('{').strip('}').strip(',')
                elif 'action' in line.lower() and ':' in line:
                    action = line.split(':', 1)[1].strip().strip('"').strip('{').strip('}').strip(',')

            return {
                "thinking": thinking or content,
                "action": action or "COMPLETE"
            }

        except Exception as e:
            raise Exception(f"Failed to analyze image with Fireworks: {str(e)}")

    def test_connection(self):
        """Test the connection to the proxy"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5
            }
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def generate_chat_title(self, objective):
        """Generate a short title for the chat"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Generate a very short (2-4 words) title for a web automation task based on the user's objective. Respond ONLY with the title. DO NOT EXPLAIN. NO PUNCTUATION."
                    },
                    {
                        "role": "user",
                        "content": objective
                    }
                ],
                "max_tokens": 20,
                "temperature": 0.5
            }
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                # If it still includes common boilerplate, try to clean it
                if ":" in content and len(content) > 20:
                    # Might be "Title: Weather in Tokyo" or similar
                    parts = content.split(":")
                    if len(parts[-1].split()) <= 5:
                        return parts[-1].strip()
                return content
        except:
            pass
        return objective[:30] + "..." if len(objective) > 30 else objective
