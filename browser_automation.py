import os
import time
import base64
from datetime import datetime
from firecrawl import FirecrawlApp
import traceback
import json
import io
from PIL import Image

class BrowserAutomation:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("Firecrawl API key is required")
        self.app = FirecrawlApp(api_key=self.api_key)
        self.session_id = None
        self.screenshot_counter = 1
        self.element_map = {}  # Maps indexes to elements info
        
    def start_browser(self):
        """Start Firecrawl browser session"""
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs('screenshots', exist_ok=True)
            
            # Launch a session
            response = self.app.browser()
            
            if hasattr(response, 'id'):
                self.session_id = response.id
            elif isinstance(response, dict):
                self.session_id = response.get('id')
            
            if not self.session_id:
                error_msg = getattr(response, 'error', 'Unknown error') if hasattr(response, 'error') else 'Failed to get session ID'
                raise Exception(f"Failed to start Firecrawl browser: {error_msg}")
            
            print(f"Firecrawl browser session started: {self.session_id}")
            
            # Navigate to a default page
            self.navigate_to('https://www.google.com')
            
            return True
            
        except Exception as e:
            print(f"Failed to start Firecrawl browser: {str(e)}")
            print(traceback.format_exc())
            raise e
    
    def take_screenshot(self):
        """Take a screenshot using Playwright in the sandbox"""
        if not self.session_id:
            raise Exception("Browser not started")
        
        try:
            # Use playwright-based screenshot
            code = """
            const screenshot = await page.screenshot({ fullPage: false });
            console.log(screenshot.toString('base64'));
            """
            result = self.app.browser_execute(self.session_id, code, language="node")

            # The result object attributes: success, stdout, result, stderr, etc.
            if not result.success:
                raise Exception(f"Failed to take screenshot: {result.stderr}")

            image_data = result.stdout.strip()
            # If there's multiple things in stdout, try to find the base64 part
            if '\n' in image_data:
                image_data = image_data.split('\n')[-1].strip()

            image_bytes = base64.b64decode(image_data)

            # Detect image format
            try:
                img = Image.open(io.BytesIO(image_bytes))
                extension = img.format.lower()
            except Exception as e:
                print(f"Warning: Could not detect image format, defaulting to png: {e}")
                extension = "png"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{self.screenshot_counter:03d}_{timestamp}.{extension}"
            filepath = os.path.join('screenshots', filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            self.screenshot_counter += 1
            return filepath

        except Exception as e:
            print(f"Error taking screenshot: {str(e)}")
            raise e
    
    def get_interactable_elements(self):
        """Get all interactable elements using Playwright in the sandbox"""
        if not self.session_id:
            raise Exception("Browser not started")
        
        code = """
        const elements = await page.evaluate(() => {
            const interactableSelectors = [
                'a', 'button', 'input', 'textarea', 'select',
                '[onclick]', '[role="button"]', '[tabindex]',
                '.btn', '.button'
            ];

            const found = [];
            interactableSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 &&
                        window.getComputedStyle(el).visibility !== 'hidden' &&
                        window.getComputedStyle(el).display !== 'none') {
                        found.push({
                            x: rect.left,
                            y: rect.top,
                            width: rect.width,
                            height: rect.height,
                            tagName: el.tagName,
                            type: el.type,
                            text: (el.innerText || el.value || '').substring(0, 50)
                        });
                    }
                });
            });

            // Deduplicate (approximate by position)
            const unique = [];
            const seen = new Set();
            for (const el of found) {
                const key = `${Math.round(el.x)},${Math.round(el.y)}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    unique.push(el);
                }
            }

            return unique.sort((a, b) => (a.y - b.y) || (a.x - b.x));
        });
        console.log(JSON.stringify(elements));
        """
        
        try:
            result = self.app.browser_execute(self.session_id, code, language="node")

            if not result.success:
                raise Exception(f"Failed to get elements: {result.stderr}")

            elements_json = result.stdout.strip()
            if '\n' in elements_json:
                elements_json = elements_json.split('\n')[-1].strip()

            elements = json.loads(elements_json)

            self.element_map = {}
            for i, element in enumerate(elements, 1):
                self.element_map[i] = element

            return self.element_map

        except Exception as e:
            print(f"Error getting elements: {str(e)}")
            return {}
    
    def click_element_by_index(self, index):
        """Click an element by its index"""
        if not self.session_id:
            raise Exception("Browser not started")
        
        if index not in self.element_map:
            raise Exception(f"Element with index {index} not found")
        
        element = self.element_map[index]
        
        code = f"""
        await page.mouse.click({element['x'] + element['width']/2}, {element['y'] + element['height']/2});
        """

        try:
            result = self.app.browser_execute(self.session_id, code, language="node")
            
            if not result.success:
                raise Exception(f"Failed to click: {result.stderr}")

            time.sleep(1)
        except Exception as e:
            raise Exception(f"Failed to click element: {str(e)}")
    
    def type_text(self, text, element_description):
        """Type text into an element found by description"""
        if not self.session_id:
            raise Exception("Browser not started")
        
        code = f"""
        // Find element by description
        const description = "{element_description.replace('"', '\\"').lower()}";
        const target = await page.evaluate((desc) => {{
            const inputs = Array.from(document.querySelectorAll('input, textarea'));
            return inputs.find(el => {{
                const placeholder = (el.placeholder || '').toLowerCase();
                const name = (el.name || '').toLowerCase();
                const id = (el.id || '').toLowerCase();
                const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();

                return placeholder.includes(desc) ||
                       name.includes(desc) ||
                       id.includes(desc) ||
                       ariaLabel.includes(desc);
            }})?.getBoundingClientRect();
        }}, description);
        
        if (target) {{
            await page.mouse.click(target.left + target.width/2, target.top + target.height/2);
            await page.keyboard.type("{text.replace('"', '\\"')}");
            await page.keyboard.press('Enter');
        }} else {{
            // Fallback: try to just type if an element is focused, or find ANY visible input
            await page.keyboard.type("{text.replace('"', '\\"')}");
            await page.keyboard.press('Enter');
        }}
        """
        
        try:
            result = self.app.browser_execute(self.session_id, code, language="node")

            if not result.success:
                raise Exception(f"Failed to type: {result.stderr}")

            time.sleep(1)
        except Exception as e:
            raise Exception(f"Failed to type text: {str(e)}")
    
    def navigate_to(self, url):
        """Navigate to a specific URL"""
        if not self.session_id:
            raise Exception("Browser not started")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        code = f'await page.goto("{url}", {{ waitUntil: "networkidle" }});'

        try:
            result = self.app.browser_execute(self.session_id, code, language="node")

            if not result.success:
                # Try without networkidle if it fails
                code = f'await page.goto("{url}");'
                self.app.browser_execute(self.session_id, code, language="node")

            time.sleep(2)
        except Exception as e:
            raise Exception(f"Failed to navigate to {url}: {str(e)}")
    
    def get_page_info(self):
        """Get current page information"""
        if not self.session_id:
            raise Exception("Browser not started")
        
        code = """
        console.log(JSON.stringify({
            title: await page.title(),
            url: page.url()
        }));
        """

        try:
            result = self.app.browser_execute(self.session_id, code, language="node")

            if result.success:
                output = result.stdout.strip()
                if '\n' in output:
                    output = output.split('\n')[-1].strip()
                return json.loads(output)
        except:
            pass

        return {'title': 'Unknown', 'url': 'Unknown'}
    
    def close(self):
        """Close the Firecrawl browser session"""
        if self.session_id:
            try:
                self.app.delete_browser(self.session_id)
            except:
                pass
            self.session_id = None
            self.element_map = {}
            print("Firecrawl browser session closed")
