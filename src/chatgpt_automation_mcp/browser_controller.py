"""
Browser-based ChatGPT controller using Playwright
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout

try:
    from .config import Config
except ImportError:
    # For direct execution
    from config import Config

logger = logging.getLogger(__name__)


class ChatGPTBrowserController:
    """Controls ChatGPT web interface via Playwright"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.config = Config()
        
    async def __aenter__(self):
        await self.launch()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def launch(self) -> None:
        """Launch browser and navigate to ChatGPT"""
        if self.page:
            logger.debug("Browser already launched")
            return
            
        logger.info("Launching browser...")
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            "headless": self.config.HEADLESS,
            "args": ["--no-sandbox"] if self.config.HEADLESS else []
        }
        
        # Context options for session persistence
        context_options = {
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "viewport": {"width": 1280, "height": 800}
        }
        
        # Load existing session if available
        if self.config.PERSIST_SESSION:
            session_path = self.config.SESSION_DIR / f"{self.config.SESSION_NAME}.json"
            if session_path.exists():
                logger.info(f"Loading session from {session_path}")
                context_options["storage_state"] = str(session_path)
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # Navigate to ChatGPT
        logger.info("Navigating to ChatGPT...")
        await self.page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=60000)
        
        # Check if login is needed
        if await self._needs_login():
            await self._handle_login()
            
        logger.info("Browser launched successfully")
        
    async def close(self) -> None:
        """Close browser and cleanup"""
        if self.config.PERSIST_SESSION and self.context:
            session_path = self.config.SESSION_DIR / f"{self.config.SESSION_NAME}.json"
            logger.info(f"Saving session to {session_path}")
            await self.context.storage_state(path=str(session_path))
            
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        
    async def _needs_login(self) -> bool:
        """Check if login is required"""
        try:
            # Look for login button or email input
            login_indicators = [
                'button:has-text("Log in")',
                'button:has-text("Sign up")',
                'input[type="email"]',
                'a[href*="auth0.openai.com"]'
            ]
            
            for selector in login_indicators:
                if await self.page.locator(selector).count() > 0:
                    return True
                    
            # Check if we can see the main chat interface
            chat_indicators = [
                '#prompt-textarea',
                '[data-testid="conversation-turn"]',
                'button:has-text("New chat")'
            ]
            
            for selector in chat_indicators:
                if await self.page.locator(selector).count() > 0:
                    return False
                    
            return True
            
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            return True
            
    async def _handle_login(self) -> None:
        """Handle login flow"""
        logger.info("Login required...")
        
        if not self.config.CHATGPT_EMAIL:
            logger.warning("No credentials provided, waiting for manual login...")
            # Wait for manual login
            await self.page.wait_for_url("https://chatgpt.com/**", timeout=300000)  # 5 min timeout
            return
            
        try:
            # Click login button
            await self.page.click('button:has-text("Log in")')
            await self.page.wait_for_load_state("networkidle")
            
            # Enter email
            await self.page.fill('input[type="email"]', self.config.CHATGPT_EMAIL)
            await self.page.click('button[type="submit"]')
            
            # Wait for password field
            await self.page.wait_for_selector('input[type="password"]', timeout=10000)
            
            if self.config.CHATGPT_PASSWORD:
                await self.page.fill('input[type="password"]', self.config.CHATGPT_PASSWORD)
                await self.page.click('button[type="submit"]')
            else:
                logger.warning("No password provided, waiting for manual input...")
                
            # Wait for successful login
            await self.page.wait_for_url("https://chatgpt.com/**", timeout=60000)
            logger.info("Login successful")
            
        except PlaywrightTimeout:
            logger.error("Login timeout - manual intervention may be required")
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
            
    async def new_chat(self) -> str:
        """Start a new chat conversation"""
        if not self.page:
            await self.launch()
            
        try:
            # Look for new chat button
            new_chat_selectors = [
                'a[href="/"]',
                'button:has-text("New chat")',
                '[data-testid="new-chat-button"]'
            ]
            
            clicked = False
            for selector in new_chat_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        clicked = True
                        break
                except Exception:
                    continue
                    
            if not clicked:
                # Fallback: navigate directly
                await self.page.goto("https://chatgpt.com/", wait_until="networkidle")
                
            # Wait for input to be ready
            await self.page.wait_for_selector('#prompt-textarea', state="visible")
            return "New chat started"
            
        except Exception as e:
            logger.error(f"Failed to start new chat: {e}")
            raise
            
    async def send_message(self, message: str) -> str:
        """Send a message to ChatGPT"""
        if not self.page:
            await self.launch()
            
        try:
            # Find and fill the textarea
            textarea = self.page.locator('#prompt-textarea')
            await textarea.wait_for(state="visible")
            await textarea.fill(message)
            
            # Find and click send button
            send_selectors = [
                'button[data-testid="send-button"]',
                'button[aria-label="Send prompt"]',
                'button:has(svg):near(#prompt-textarea)'
            ]
            
            for selector in send_selectors:
                try:
                    button = self.page.locator(selector)
                    if await button.count() > 0 and await button.is_enabled():
                        await button.click()
                        return "Message sent"
                except Exception:
                    continue
                    
            # Fallback: press Enter
            await textarea.press("Enter")
            return "Message sent (via Enter)"
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
            
    async def wait_for_response(self, timeout: int = 30) -> bool:
        """Wait for ChatGPT to finish responding"""
        if not self.page:
            return False
            
        try:
            # Wait for thinking indicator to appear and disappear
            thinking_selectors = [
                '[data-testid="thinking-indicator"]',
                '.animate-pulse',
                'div:has-text("Thinking")',
                'button:has-text("Stop generating")'
            ]
            
            # First wait for any thinking indicator
            for selector in thinking_selectors:
                try:
                    await self.page.wait_for_selector(selector, state="visible", timeout=5000)
                    break
                except PlaywrightTimeout:
                    continue
                    
            # Then wait for it to disappear
            for selector in thinking_selectors:
                try:
                    await self.page.wait_for_selector(selector, state="hidden", timeout=timeout * 1000)
                except PlaywrightTimeout:
                    continue
                    
            # Additional wait for network idle
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            return True
            
        except Exception as e:
            logger.warning(f"Error waiting for response: {e}")
            return False
            
    async def get_last_response(self) -> Optional[str]:
        """Get the last response from ChatGPT"""
        if not self.page:
            return None
            
        try:
            # Get all conversation turns
            turns = await self.page.locator('[data-testid="conversation-turn"]').all()
            
            if not turns:
                return None
                
            # Get the last turn (should be assistant's response)
            last_turn = turns[-1]
            
            # Extract text content
            text_content = await last_turn.inner_text()
            
            # Clean up the text (remove metadata like "ChatGPT" label)
            lines = text_content.strip().split('\n')
            if lines and lines[0] in ["ChatGPT", "GPT-4", "o1", "o3"]:
                lines = lines[1:]
                
            return '\n'.join(lines).strip()
            
        except Exception as e:
            logger.error(f"Failed to get last response: {e}")
            return None
            
    async def get_conversation(self) -> List[Dict[str, str]]:
        """Get the full conversation history"""
        if not self.page:
            return []
            
        try:
            conversation = []
            turns = await self.page.locator('[data-testid="conversation-turn"]').all()
            
            for i, turn in enumerate(turns):
                text = await turn.inner_text()
                role = "user" if i % 2 == 0 else "assistant"
                
                # Clean up text
                lines = text.strip().split('\n')
                if lines and lines[0] in ["You", "ChatGPT", "GPT-4", "o1", "o3"]:
                    lines = lines[1:]
                    
                conversation.append({
                    "role": role,
                    "content": '\n'.join(lines).strip()
                })
                
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return []
            
    async def get_current_model(self) -> Optional[str]:
        """Get the currently selected model"""
        if not self.page:
            return None
            
        try:
            # Look for model indicator
            model_selectors = [
                '[data-testid="model-picker"] span',
                'button[aria-haspopup="menu"] span',
                '.model-selector span'
            ]
            
            for selector in model_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.count() > 0:
                        return await element.inner_text()
                except Exception:
                    continue
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current model: {e}")
            return None
            
    async def select_model(self, model: str) -> bool:
        """Select a specific model"""
        if not self.page:
            await self.launch()
            
        try:
            # Click model picker
            picker_selectors = [
                '[data-testid="model-picker"]',
                'button[aria-haspopup="menu"]',
                '.model-selector'
            ]
            
            for selector in picker_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        break
                except Exception:
                    continue
                    
            # Wait for menu to open
            await asyncio.sleep(0.5)
            
            # Map model names to UI text
            model_map = {
                "gpt-4": "GPT-4",
                "gpt-4.5": "GPT-4.5",
                "o1": "o1",
                "o1-preview": "o1-preview", 
                "o1-mini": "o1-mini",
                "o3": "o3",
                "o3-mini": "o3-mini"
            }
            
            ui_model = model_map.get(model.lower(), model)
            
            # Click on the model option
            model_option = self.page.locator(f'div[role="menuitem"]:has-text("{ui_model}")')
            if await model_option.count() > 0:
                await model_option.click()
                return True
            else:
                logger.warning(f"Model {model} not found in picker")
                return False
                
        except Exception as e:
            logger.error(f"Failed to select model: {e}")
            return False
            
    async def is_ready(self) -> bool:
        """Check if ChatGPT interface is ready"""
        if not self.page:
            return False
            
        try:
            # Check for main input area
            textarea = await self.page.locator('#prompt-textarea').count()
            return textarea > 0
        except Exception:
            return False
            
    async def send_and_get_response(self, message: str, timeout: int = 120) -> Optional[str]:
        """Send message and wait for complete response"""
        await self.send_message(message)
        await self.wait_for_response(timeout)
        return await self.get_last_response()
        
    async def take_screenshot(self, name: str = "chatgpt") -> Optional[Path]:
        """Take a screenshot for debugging"""
        if not self.page:
            return None
            
        try:
            path = self.config.get_screenshot_path(name)
            await self.page.screenshot(path=str(path))
            return path
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None


# Test function for direct execution
def test_browser_controller():
    """Test the browser controller"""
    async def _test():
        controller = ChatGPTBrowserController()
        
        try:
            await controller.launch()
            print(f"Ready: {await controller.is_ready()}")
            
            await controller.new_chat()
            print("Started new chat")
            
            model = await controller.get_current_model()
            print(f"Current model: {model}")
            
            response = await controller.send_and_get_response("Say 'Hello, browser automation!'")
            print(f"Response: {response}")
            
        finally:
            await controller.close()
    
    asyncio.run(_test())


if __name__ == "__main__":
    test_browser_controller()