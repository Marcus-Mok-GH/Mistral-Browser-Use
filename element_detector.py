import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

class ElementDetector:
    def __init__(self):
        self.font_size = 16
        self.circle_radius = 12
        self.circle_color = (255, 0, 0)  # Red
        self.text_color = (255, 255, 255)  # White
        
    def detect_and_annotate_elements(self, screenshot_path, browser_automation=None):
        """Detect interactive elements and annotate them with indexes"""
        try:
            # Check if file exists and is not empty
            if not os.path.exists(screenshot_path) or os.path.getsize(screenshot_path) == 0:
                raise Exception(f"Screenshot file {screenshot_path} is missing or empty")

            # Load the screenshot
            try:
                image = Image.open(screenshot_path)
                image.verify() # Verify it's an image
                image = Image.open(screenshot_path) # Re-open because verify() closes the file or moves the pointer
            except Exception as e:
                raise Exception(f"Invalid image file {screenshot_path}: {e}")
            
            # Create a copy for annotation
            annotated_image = image.copy()
            draw = ImageDraw.Draw(annotated_image)
            
            # Try to load a font, fallback to default if not available
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.font_size)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", self.font_size)
                except:
                    font = ImageFont.load_default()
            
            # Get element positions from browser if provided
            positions = {}
            if browser_automation:
                positions = self.get_element_positions_from_browser(browser_automation)
            
            # Annotate each element
            for index, (x, y, width, height) in positions.items():
                # Calculate center position
                center_x = x + width // 2
                center_y = y + height // 2
                
                # Draw red circle
                circle_bbox = [
                    center_x - self.circle_radius,
                    center_y - self.circle_radius,
                    center_x + self.circle_radius,
                    center_y + self.circle_radius
                ]
                draw.ellipse(circle_bbox, fill=self.circle_color, outline=self.circle_color)
                
                # Draw index number in white
                text = str(index)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                text_x = center_x - text_width // 2
                text_y = center_y - text_height // 2
                
                draw.text((text_x, text_y), text, fill=self.text_color, font=font)
            
            # Save the annotated image
            base_name, extension = os.path.splitext(screenshot_path)
            annotated_path = f"{base_name}_annotated{extension}"
            annotated_image.save(annotated_path)
            
            return annotated_path
            
        except Exception:
            return screenshot_path  # Return original if annotation fails
    
    def annotate_elements_with_positions(self, screenshot_path, element_positions):
        """Annotate elements given their positions"""
        try:
            # Check if file exists and is not empty
            if not os.path.exists(screenshot_path) or os.path.getsize(screenshot_path) == 0:
                raise Exception(f"Screenshot file {screenshot_path} is missing or empty")

            # Load the screenshot
            try:
                image = Image.open(screenshot_path)
                image.verify()
                image = Image.open(screenshot_path)
            except Exception as e:
                raise Exception(f"Invalid image file {screenshot_path}: {e}")

            annotated_image = image.copy()
            draw = ImageDraw.Draw(annotated_image)
            
            # Try to load a font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.font_size)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", self.font_size)
                except:
                    font = ImageFont.load_default()
            
            # Annotate each element
            for index, (x, y, width, height) in element_positions.items():
                # Calculate center position
                center_x = x + width // 2
                center_y = y + height // 2
                
                # Draw red circle
                circle_bbox = [
                    center_x - self.circle_radius,
                    center_y - self.circle_radius,
                    center_x + self.circle_radius,
                    center_y + self.circle_radius
                ]
                draw.ellipse(circle_bbox, fill=self.circle_color, outline=self.circle_color)
                
                # Draw index number in white
                text = str(index)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                text_x = center_x - text_width // 2
                text_y = center_y - text_height // 2
                
                draw.text((text_x, text_y), text, fill=self.text_color, font=font)
            
            # Save annotated image
            base_name, extension = os.path.splitext(screenshot_path)
            annotated_path = f"{base_name}_annotated{extension}"
            annotated_image.save(annotated_path)
            
            return annotated_path
            
        except Exception:
            return screenshot_path
    
    def get_element_positions_from_browser(self, browser_automation):
        """Extract element positions from browser automation instance"""
        if not browser_automation or not browser_automation.session_id:
            return {}
        
        try:
            # Get interactable elements
            element_map = browser_automation.get_interactable_elements()
            
            positions = {}
            for index, element in element_map.items():
                try:
                    positions[index] = (
                        element['x'],
                        element['y'],
                        element['width'],
                        element['height']
                    )
                except:
                    continue
            
            return positions
            
        except Exception:
            return {}
    
    def create_annotated_screenshot(self, browser_automation):
        """Take screenshot and annotate with element indexes"""
        try:
            if not browser_automation:
                raise Exception("Browser automation instance required")
            
            # Take screenshot
            screenshot_path = browser_automation.take_screenshot()
            
            # Get element positions
            positions = self.get_element_positions_from_browser(browser_automation)
            
            if not positions:
                return screenshot_path
            
            # Annotate with positions
            annotated_path = self.annotate_elements_with_positions(screenshot_path, positions)
            
            return annotated_path
            
        except Exception:
            return None
