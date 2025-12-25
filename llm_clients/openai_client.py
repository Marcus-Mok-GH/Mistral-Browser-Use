
import requests
import json
import base64
import os
from llm_clients.base_client import BaseClient

class OpenAIClient(BaseClient):
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o"
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    def analyze_and_decide(self, image_base64, user_objective, current_context=None):
        """Analyze screenshot and decide on next action"""
        
        system_prompt = """You are a web automation assistant powered by computer vision. Your task is to analyze screenshots of web pages and determine the next action to take to achieve the user's objective.

AVAILABLE ACTIONS:
- click(INDEX) - Click on an element by its numbered index (shown in red circles)
- type("TEXT", into="ELEMENT") - Type text into an input field (specify element by description)
- press_key("KEY_NAME"): Simulates pressing a special key on the keyboard. KEY_NAME should be one of ["enter", "escape", "tab"]. Use "enter" for submitting forms or search queries after typing, "escape" for closing dialogs, or "tab" to navigate form elements.
- COMPLETE - When the objective is achieved

RESPONSE FORMAT:
Return a JSON object with exactly these fields:
{
    "thinking": "Your reasoning about what you see and what to do next",
    "action": "The specific action to take (e.g., click(5) or type('hello', into='search box') or COMPLETE)"
}

GUIDELINES:
- Carefully examine all numbered elements in the image
- Choose the most logical next step toward the objective
- Be specific with element indexes when clicking
- For typing, describe the target element clearly
- If the objective appears complete, respond with action: "COMPLETE"
- Always explain your reasoning in the thinking field"""

        user_prompt = f"""Current Objective: {user_objective}

Please analyze this screenshot and determine the next action to take. The image shows a webpage with numbered red circles indicating clickable elements. Choose the appropriate action to progress toward the objective."""

        if current_context:
            user_prompt += f"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
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
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1024,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code} - {response.text}")
            
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise Exception("No response from API")
            
            content = result['choices'][0]['message']['content']
            
            # OpenAI's gpt-4o with json mode is still in beta, so we'll parse the string
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                raise Exception("Failed to decode JSON from response")
            
        except Exception as e:
            raise Exception(f"Failed to analyze image: {str(e)}")
    
    def test_connection(self):
        """Test the API connection"""
        # For OpenAI, we can list models as a simple connection test
        # This is a lightweight and reliable way to check API key and connectivity
        return True
