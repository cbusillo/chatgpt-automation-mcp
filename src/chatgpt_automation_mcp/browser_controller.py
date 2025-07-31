"""
Browser-based ChatGPT controller using Playwright
"""

import asyncio
import logging
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeout,
)

try:
    from .config import Config
    from .error_recovery import ChatGPTErrorRecovery
except ImportError:
    # For direct execution
    from config import Config
    from error_recovery import ChatGPTErrorRecovery

logger = logging.getLogger(__name__)


class ChatGPTBrowserController:
    """Controls ChatGPT web interface via Playwright"""

    def __init__(self):
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.playwright = None
        self.config = Config()
        self.error_recovery: ChatGPTErrorRecovery | None = None
        self.is_cdp_connection = False

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def launch(self) -> None:
        """Launch browser and navigate to ChatGPT with error recovery"""
        if self.page:
            logger.debug("Browser already launched")
            return

        try:
            logger.info("Launching browser...")
            self.playwright = await async_playwright().start()

            # Try CDP connection first if enabled
            if self.config.USE_CDP:
                try:
                    logger.info(f"Attempting CDP connection to {self.config.CDP_URL}")
                    self.browser = await self.playwright.chromium.connect_over_cdp(
                        self.config.CDP_URL
                    )
                    # Get existing contexts
                    contexts = self.browser.contexts
                    if contexts:
                        self.context = contexts[0]
                        pages = self.context.pages
                        # Find ChatGPT tab or create new one
                        chatgpt_page = None
                        for page in pages:
                            if "chatgpt.com" in page.url or "chat.openai.com" in page.url:
                                chatgpt_page = page
                                break
                        
                        if chatgpt_page:
                            self.page = chatgpt_page
                            logger.info("Connected to existing ChatGPT tab")
                        else:
                            self.page = await self.context.new_page()
                            logger.info("Created new tab in existing browser")
                    else:
                        # No contexts, create one
                        self.context = await self.browser.new_context()
                        self.page = await self.context.new_page()
                        logger.info("Created new context in CDP browser")
                    
                    logger.info("Successfully connected via CDP")
                    self.is_cdp_connection = True
                except Exception as e:
                    logger.warning(f"CDP connection failed: {e}, falling back to regular launch")
                    # Fall through to regular launch
                    self.browser = None
                    self.context = None
                    self.page = None
            
            # Regular launch if CDP not used or failed
            if not self.browser:
                # Browser launch options
                launch_options = {
                    "headless": self.config.HEADLESS,
                    "args": ["--no-sandbox"] if self.config.HEADLESS else [],
                }

                # Context options for session persistence
                context_options = {
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                    "viewport": {"width": 1280, "height": 800},
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
            await self.page.goto(
                "https://chatgpt.com", wait_until="domcontentloaded", timeout=60000
            )

            # Check if login is needed
            if await self._needs_login():
                await self._handle_login()

            logger.info("Browser launched successfully")

            # Initialize error recovery system
            if not self.error_recovery:
                self.error_recovery = ChatGPTErrorRecovery(self)

        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            await self.close()

            # For critical browser launch failures, try once more after cleanup
            if "browser" in str(e).lower() or "playwright" in str(e).lower():
                logger.info("Attempting to restart browser after failure...")
                try:
                    await asyncio.sleep(3)
                    # Reset state and try again
                    self.browser = None
                    self.context = None
                    self.page = None
                    self.playwright = None
                    return await self.launch()
                except Exception as retry_error:
                    logger.error(f"Browser restart failed: {retry_error}")
                    raise retry_error
            raise

    async def close(self) -> None:
        """Close browser and cleanup"""
        # Save session if not using CDP (CDP uses existing browser session)
        if self.config.PERSIST_SESSION and self.context and not self.config.USE_CDP:
            session_path = self.config.SESSION_DIR / f"{self.config.SESSION_NAME}.json"
            logger.info(f"Saving session to {session_path}")
            await self.context.storage_state(path=str(session_path))

        # For CDP connections, we don't close the browser (it's the user's main browser)
        if self.is_cdp_connection:
            logger.info("CDP mode: Keeping browser open (user's main browser)")
            # Just disconnect, don't close anything
            if self.playwright:
                await self.playwright.stop()
        else:
            # Normal cleanup for standalone browser
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
                'a[href*="auth0.openai.com"]',
            ]

            for selector in login_indicators:
                if await self.page.locator(selector).count() > 0:
                    return True

            # Check if we can see the main chat interface
            chat_indicators = [
                "#prompt-textarea",
                '[data-testid="conversation-turn"]',
                'button:has-text("New chat")',
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
        """Start a new chat conversation with error recovery"""
        if not self.page:
            await self.launch()

        try:
            return await self._new_chat_impl()
        except Exception as e:
            # Try error recovery if available
            if self.error_recovery:
                recovery_successful = await self.error_recovery.handle_error(e, "new_chat")
                if recovery_successful:
                    # Retry the operation once after recovery
                    try:
                        return await self._new_chat_impl()
                    except Exception as retry_error:
                        logger.error(f"New chat retry failed: {retry_error}")
                        raise retry_error
            logger.error(f"Failed to start new chat: {e}")
            raise

    async def _new_chat_impl(self) -> str:
        """Implementation of new chat logic"""
        # Look for new chat button
        new_chat_selectors = [
            'a[href="/"]',
            'button:has-text("New chat")',
            '[data-testid="new-chat-button"]',
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
        await self.page.wait_for_selector("#prompt-textarea", state="visible")
        return "New chat started"

    async def send_message(self, message: str) -> str:
        """Send a message to ChatGPT with error recovery"""
        if not self.page:
            await self.launch()

        try:
            # Find and fill the textarea
            textarea = self.page.locator("#prompt-textarea")
            await textarea.wait_for(state="visible")
            await textarea.fill(message)

            # Find and click send button
            send_selectors = [
                'button[data-testid="send-button"]',
                'button[aria-label="Send prompt"]',
                "button:has(svg):near(#prompt-textarea)",
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
            # Try error recovery if available
            if self.error_recovery:
                recovery_successful = await self.error_recovery.handle_error(e, "send_message")
                if recovery_successful:
                    # Retry the operation once after recovery
                    try:
                        # Retry the same logic
                        textarea = self.page.locator("#prompt-textarea")
                        await textarea.wait_for(state="visible")
                        await textarea.fill(message)

                        # Try to find and click the send button
                        send_selectors = [
                            'button[data-testid="send-button"]',
                            'button[aria-label="Send message"]',
                            'button:has(svg[data-testid="send-button"])',
                        ]

                        for selector in send_selectors:
                            send_button = self.page.locator(selector)
                            if await send_button.count() > 0 and await send_button.is_enabled():
                                await send_button.click()
                                return "Message sent"

                        # Fallback: press Enter
                        await textarea.press("Enter")
                        return "Message sent (via Enter)"
                    except Exception as retry_error:
                        logger.error(f"Failed to send message after recovery: {retry_error}")
                        raise retry_error

            logger.error(f"Failed to send message: {e}")
            raise

    async def wait_for_response(self, timeout: int = 30) -> bool:
        """Wait for ChatGPT to finish responding with error recovery"""
        if not self.page:
            return False

        try:
            return await self._wait_for_response_impl(timeout)
        except Exception as e:
            # Try error recovery if available
            if self.error_recovery:
                recovery_successful = await self.error_recovery.handle_error(e, "wait_for_response")
                if recovery_successful:
                    # Retry the operation once after recovery
                    try:
                        return await self._wait_for_response_impl(timeout)
                    except Exception as retry_error:
                        logger.error(f"Wait for response retry failed: {retry_error}")
                        return False
            logger.warning(f"Error waiting for response: {e}")
            return False

    async def _wait_for_response_impl(self, timeout: int) -> bool:
        """Implementation of wait for response logic"""
        # Wait for thinking indicator to appear and disappear
        thinking_selectors = [
            '[data-testid="thinking-indicator"]',
            ".animate-pulse",
            'div:has-text("Thinking")',
            'button:has-text("Stop generating")',
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

    async def get_last_response(self) -> str | None:
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
            lines = text_content.strip().split("\n")
            if lines and lines[0] in ["ChatGPT", "GPT-4", "o1", "o3"]:
                lines = lines[1:]

            return "\n".join(lines).strip()

        except Exception as e:
            logger.error(f"Failed to get last response: {e}")
            return None

    async def get_conversation(self) -> list[dict[str, str]]:
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
                lines = text.strip().split("\n")
                if lines and lines[0] in ["You", "ChatGPT", "GPT-4", "o1", "o3"]:
                    lines = lines[1:]

                conversation.append({"role": role, "content": "\n".join(lines).strip()})

            return conversation

        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return []

    async def get_current_model(self) -> str | None:
        """Get the currently selected model with error recovery"""
        if not self.page:
            return None

        try:
            return await self._get_current_model_impl()
        except Exception as e:
            # Try error recovery if available
            if self.error_recovery:
                recovery_successful = await self.error_recovery.handle_error(e, "get_current_model")
                if recovery_successful:
                    # Retry the operation once after recovery
                    try:
                        return await self._get_current_model_impl()
                    except Exception as retry_error:
                        logger.error(f"Model detection retry failed: {retry_error}")
                        return None
            logger.error(f"Failed to get current model: {e}")
            return None

    async def _get_current_model_impl(self) -> str | None:
        """Implementation of model detection logic"""
        # Look for model indicator with improved selectors
        model_selectors = [
            '[data-testid="model-picker"] span',
            'button[aria-haspopup="menu"] span',
            "button[data-state] span",  # New UI pattern
            "div[data-radix-popper-content-wrapper] button span",  # Dropdown button
            ".model-selector span",
            "button:has(svg.icon-chevron-down) span",  # Button with dropdown icon
            "nav button span",  # Sometimes in nav
        ]

        for selector in model_selectors:
            try:
                elements = self.page.locator(selector)
                count = await elements.count()
                for i in range(min(count, 5)):  # Check first 5 matches
                    element = elements.nth(i)
                    if await element.is_visible():
                        text = await element.inner_text()
                        # Validate it's a model name
                        if any(model in text.lower() for model in ["gpt", "o1", "o3", "claude"]):
                            return text.strip()
            except Exception:
                continue

        # Fallback: Check conversation metadata
        try:
            # Sometimes model info is in page title or hidden metadata
            title = await self.page.title()
            if "GPT" in title or "o1" in title or "o3" in title:
                for model in ["GPT-4.5", "GPT-4", "o3-mini", "o3", "o1-mini", "o1"]:
                    if model in title:
                        return model
        except Exception:
            pass

        return None

    async def select_model(self, model: str) -> bool:
        """Select a specific model with improved reliability and error recovery"""
        if not self.page:
            await self.launch()

        try:
            return await self._select_model_impl(model)
        except Exception as e:
            # Try error recovery if available
            if self.error_recovery:
                recovery_successful = await self.error_recovery.handle_error(e, "select_model")
                if recovery_successful:
                    # Retry the operation once after recovery
                    try:
                        return await self._select_model_impl(model)
                    except Exception as retry_error:
                        logger.error(f"Model selection retry failed: {retry_error}")
                        return False
            logger.error(f"Failed to select model: {e}")
            return False

    async def _select_model_impl(self, model: str) -> bool:
        """Implementation of model selection logic"""
        # First check if we're already on the requested model
        current = await self.get_current_model()
        if current and model.lower() in current.lower():
            logger.info(f"Already using model: {current}")
            return True

        # Click model picker with improved selectors
        picker_selectors = [
            '[data-testid="model-picker"]',
            'button[aria-haspopup="menu"]:has(span)',
            "button[data-state]:has(span)",
            "button:has(svg.icon-chevron-down)",
            "nav button:has(span)",
            ".model-selector",
            'div[role="combobox"]',
        ]

        clicked = False
        for selector in picker_selectors:
            try:
                elements = self.page.locator(selector)
                count = await elements.count()
                for i in range(min(count, 3)):
                    element = elements.nth(i)
                    if await element.is_visible():
                        # Check if it contains model-related text
                        text = await element.text_content() or ""
                        if any(m in text.lower() for m in ["gpt", "o1", "o3", "model"]):
                            await element.click()
                            clicked = True
                            break
                if clicked:
                    break
            except Exception:
                continue

        if not clicked:
            logger.warning("Could not find model picker")
            return False

        # Wait for menu to open with better detection
        await self.page.wait_for_selector(
            '[role="menu"], [role="listbox"], [data-radix-menu-content]',
            state="visible",
            timeout=5000,
        )
        await asyncio.sleep(0.3)  # Small delay for animation

        # Enhanced model name mapping
        model_map = {
            "gpt-4": ["GPT-4", "gpt-4", "GPT 4"],
            "gpt-4.5": ["GPT-4.5", "gpt-4.5", "GPT 4.5", "ChatGPT Plus"],
            "4o": ["GPT-4o", "4o", "gpt-4o"],
            "o1": ["o1", "O1"],
            "o1-preview": ["o1-preview", "O1 Preview", "o1 preview"],
            "o1-mini": ["o1-mini", "O1 Mini", "o1 mini"],
            "o3": ["o3", "O3"],
            "o3-mini": ["o3-mini", "O3 Mini", "o3 mini"],
        }

        # Get possible UI texts for the model
        ui_models = model_map.get(model.lower(), [model])
        if not isinstance(ui_models, list):
            ui_models = [ui_models]

        # Try to find and click the model option
        option_selectors = [
            'div[role="menuitem"]',
            'div[role="option"]',
            'button[role="menuitem"]',
            'li[role="option"]',
            "[data-radix-menu-item]",
        ]

        for ui_model in ui_models:
            for selector in option_selectors:
                try:
                    # Try exact match first
                    option = self.page.locator(f'{selector}:has-text("{ui_model}")').first
                    if await option.count() > 0 and await option.is_visible():
                        await option.click()
                        await asyncio.sleep(0.5)  # Wait for selection

                        # Verify selection
                        new_model = await self.get_current_model()
                        if new_model and ui_model.lower() in new_model.lower():
                            logger.info(f"Successfully selected model: {new_model}")
                            return True
                except Exception:
                    continue

        logger.warning(f"Model {model} not found in picker")
        return False

    async def is_ready(self) -> bool:
        """Check if ChatGPT interface is ready"""
        if not self.page:
            return False

        try:
            # Check for main input area
            textarea = await self.page.locator("#prompt-textarea").count()
            return textarea > 0
        except Exception:
            return False

    async def send_and_get_response(self, message: str, timeout: int = 120) -> str | None:
        """Send message and wait for complete response"""
        await self.send_message(message)
        await self.wait_for_response(timeout)
        return await self.get_last_response()

    async def take_screenshot(self, name: str = "chatgpt") -> Path | None:
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

    async def toggle_search_mode(self, enable: bool) -> bool:
        """Toggle web search mode on or off"""
        if not self.page:
            await self.launch()

        try:
            # Look for the search toggle
            # ChatGPT uses different selectors over time, try multiple
            toggle_selectors = [
                'button[aria-label*="Search"]',
                'button:has-text("Search the web")',
                '[data-testid="search-toggle"]',
                'label:has-text("Search")',
            ]

            for selector in toggle_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.count() > 0:
                        # Check current state
                        is_checked = (
                            await element.is_checked()
                            if await element.get_attribute("type") == "checkbox"
                            else None
                        )

                        # If it's a button, check aria-pressed or similar
                        if is_checked is None:
                            aria_pressed = await element.get_attribute("aria-pressed")
                            is_checked = aria_pressed == "true" if aria_pressed else None

                        # Toggle if needed
                        if is_checked is not None and is_checked != enable:
                            await element.click()
                            await asyncio.sleep(0.5)  # Wait for state change

                        return True
                except Exception:
                    continue

            logger.warning("Search toggle not found")
            return False

        except Exception as e:
            logger.error(f"Failed to toggle search mode: {e}")
            return False

    async def toggle_browsing_mode(self, enable: bool) -> bool:
        """Toggle web browsing mode on or off (alias for toggle_search_mode)

        Args:
            enable: True to enable browsing, False to disable

        Returns:
            True if successful, False otherwise
        """
        # Web browsing and search mode are the same feature in ChatGPT
        return await self.toggle_search_mode(enable)

    async def upload_file(self, file_path: str) -> bool:
        """Upload a file to the current conversation"""
        if not self.page:
            await self.launch()

        try:
            # Convert to Path object
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Look for file input
            file_input_selectors = [
                'input[type="file"]',
                '[data-testid="file-upload"]',
                'input[accept*="image"]',  # Often hidden but present
            ]

            for selector in file_input_selectors:
                try:
                    # File inputs are often hidden, so we can't check visibility
                    file_input = self.page.locator(selector).first
                    if await file_input.count() > 0:
                        # Set files on the input
                        await file_input.set_input_files(str(path))

                        # Wait a bit for upload to process
                        await asyncio.sleep(1)

                        logger.info(f"File uploaded: {path.name}")
                        return True
                except Exception as e:
                    logger.debug(f"Failed with selector {selector}: {e}")
                    continue

            # Alternative: look for a button that triggers file picker
            upload_button_selectors = [
                'button[aria-label*="Attach"]',
                'button[aria-label*="Upload"]',
                'button:has(svg[aria-label*="paperclip"])',
                '[data-testid="file-upload-button"]',
            ]

            for selector in upload_button_selectors:
                try:
                    button = self.page.locator(selector).first
                    if await button.count() > 0 and await button.is_visible():
                        # Click button and wait for file chooser
                        async with self.page.expect_file_chooser() as fc_info:
                            await button.click()
                        file_chooser = await fc_info.value

                        # Set the file
                        await file_chooser.set_files(str(path))

                        # Wait for upload
                        await asyncio.sleep(1)

                        logger.info(f"File uploaded via button: {path.name}")
                        return True
                except Exception as e:
                    logger.debug(f"Failed with button {selector}: {e}")
                    continue

            logger.warning("No file upload method found")
            return False

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False

    async def regenerate_response(self) -> bool:
        """Regenerate the last response from ChatGPT"""
        if not self.page:
            await self.launch()

        try:
            # Look for regenerate button - ChatGPT shows this after a response
            regenerate_selectors = [
                'button[aria-label*="Regenerate"]',
                'button:has-text("Regenerate")',
                'button:has-text("Regenerate response")',
                '[data-testid="regenerate-button"]',
                'button:has(svg[aria-label*="regenerate"])',
                # Sometimes it's in a menu
                'button[aria-label*="More"]',
                'button[aria-label="ChatGPT options"]',
            ]

            for selector in regenerate_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.count() > 0 and await element.is_visible():
                        # If it's the "More" menu, click it first
                        if "More" in selector or "options" in selector:
                            await element.click()
                            await asyncio.sleep(0.5)

                            # Look for regenerate in dropdown
                            dropdown_regenerate = self.page.locator('button:has-text("Regenerate")')
                            if await dropdown_regenerate.count() > 0:
                                await dropdown_regenerate.first.click()
                                logger.info("Clicked regenerate in dropdown menu")
                                return True
                        else:
                            # Direct regenerate button
                            await element.click()
                            logger.info("Clicked regenerate button")
                            return True
                except Exception as e:
                    logger.debug(f"Failed with selector {selector}: {e}")
                    continue

            # Alternative: Try keyboard shortcut if available
            # Some versions of ChatGPT support Ctrl+R or similar
            try:
                await self.page.keyboard.press("Control+r")
                await asyncio.sleep(0.5)
                # Check if regeneration started (thinking animation)
                if await self._is_responding():
                    logger.info("Triggered regeneration via keyboard shortcut")
                    return True
            except Exception:
                pass

            logger.warning("Regenerate button not found")
            return False

        except Exception as e:
            logger.error(f"Failed to regenerate response: {e}")
            return False

    async def export_conversation(self, format: str = "markdown") -> str | None:
        """Export the current conversation in specified format

        Args:
            format: Export format - "markdown" or "json"

        Returns:
            Exported conversation content or None if failed
        """
        if not self.page:
            await self.launch()

        try:
            # Get the conversation content
            conversation = await self.get_conversation()
            if not conversation:
                logger.warning("No conversation to export")
                return None

            if format == "json":
                # Return raw JSON
                import json

                return json.dumps(conversation, indent=2)

            elif format == "markdown":
                # Convert to markdown format
                md_lines = []
                md_lines.append("# ChatGPT Conversation")
                md_lines.append(f"\n**Model**: {conversation.get('model', 'Unknown')}")
                md_lines.append(f"**Date**: {conversation.get('timestamp', 'Unknown')}\n")

                messages = conversation.get("messages", [])
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")

                    if role == "user":
                        md_lines.append(f"## User\n\n{content}\n")
                    elif role == "assistant":
                        md_lines.append(f"## ChatGPT\n\n{content}\n")
                    else:
                        md_lines.append(f"## {role.title()}\n\n{content}\n")

                return "\n".join(md_lines)

            else:
                logger.error(f"Unsupported export format: {format}")
                return None

        except Exception as e:
            logger.error(f"Failed to export conversation: {e}")
            return None

    async def save_conversation(
        self, filename: str | None = None, format: str = "markdown"
    ) -> Path | None:
        """Export and save conversation to file

        Args:
            filename: Custom filename (without extension). If None, auto-generates.
            format: Export format - "markdown" or "json"

        Returns:
            Path to saved file or None if failed
        """
        try:
            # Export the conversation
            content = await self.export_conversation(format)
            if not content:
                return None

            # Determine file extension
            ext = "md" if format == "markdown" else "json"

            # Generate filename if not provided
            if not filename:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"chatgpt_conversation_{timestamp}"

            # Create full path
            file_path = self.config.EXPORT_DIR / f"{filename}.{ext}"

            # Write to file
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"Conversation saved to: {file_path}")

            return file_path

        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return None

    async def list_conversations(self) -> list[dict] | None:
        """List all available conversations

        Returns:
            List of conversation dictionaries with id, title, and timestamp
        """
        if not self.page:
            await self.launch()

        try:
            # Look for conversation list
            conversation_list_selectors = [
                '[data-testid="conversation-list"]',
                'nav[aria-label="Chat history"]',
                'div[class*="conversation-list"]',
                "div.flex.flex-col.gap-2.text-gray-100",  # Common pattern
            ]

            conversations = []
            for selector in conversation_list_selectors:
                list_element = self.page.locator(selector).first
                if await list_element.count() > 0:
                    # Find individual conversation items
                    item_selectors = [
                        'a[href^="/c/"]',  # Conversation links
                        '[data-testid="conversation-item"]',
                        'div[role="button"]',
                    ]

                    for item_sel in item_selectors:
                        items = list_element.locator(item_sel)
                        count = await items.count()
                        if count > 0:
                            for i in range(count):
                                item = items.nth(i)
                                try:
                                    # Extract conversation info
                                    text = await item.text_content()
                                    if text and text.strip():
                                        # Try to get href for ID
                                        href = await item.get_attribute("href")
                                        conv_id = href.split("/")[-1] if href else f"conv_{i}"

                                        conversations.append(
                                            {"id": conv_id, "title": text.strip(), "index": i}
                                        )
                                except Exception:
                                    continue
                            break

                    if conversations:
                        break

            logger.info(f"Found {len(conversations)} conversations")
            return conversations

        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return None

    async def switch_conversation(self, conversation_id: str | int) -> bool:
        """Switch to a different conversation

        Args:
            conversation_id: Either the conversation ID string or index number

        Returns:
            True if switch was successful
        """
        if not self.page:
            await self.launch()

        try:
            # If it's an index, get the conversation list
            if isinstance(conversation_id, int):
                conversations = await self.list_conversations()
                if not conversations or conversation_id >= len(conversations):
                    logger.error(f"Invalid conversation index: {conversation_id}")
                    return False
                conversation_id = conversations[conversation_id]["id"]

            # Navigate to conversation URL
            if conversation_id.startswith("conv_"):
                # It's an index-based ID, need to click the item
                conversations = await self.list_conversations()
                for conv in conversations:
                    if conv["id"] == conversation_id:
                        # Find and click the conversation item
                        item_selectors = [
                            f'a[href^="/c/"]:has-text("{conv["title"]}")',
                            f'[data-testid="conversation-item"]:has-text("{conv["title"]}")',
                            f'div[role="button"]:has-text("{conv["title"]}")',
                        ]

                        for selector in item_selectors:
                            item = self.page.locator(selector).first
                            if await item.count() > 0:
                                await item.click()
                                await asyncio.sleep(1)  # Wait for navigation
                                logger.info(f"Switched to conversation: {conv['title']}")
                                return True
            else:
                # Direct navigation by ID
                await self.page.goto(f"https://chatgpt.com/c/{conversation_id}")
                await self.page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1)

                # Verify we're in the right conversation
                if await self.is_ready():
                    logger.info(f"Switched to conversation: {conversation_id}")
                    return True

            logger.error("Failed to switch conversation")
            return False

        except Exception as e:
            logger.error(f"Failed to switch conversation: {e}")
            return False

    async def delete_conversation(self, conversation_id: str | int) -> bool:
        """Delete a conversation

        Args:
            conversation_id: Either the conversation ID string or index number

        Returns:
            True if deletion was successful
        """
        if not self.page:
            await self.launch()

        try:
            # First switch to the conversation
            if not await self.switch_conversation(conversation_id):
                return False

            # Look for delete/options button
            delete_selectors = [
                'button[aria-label*="Delete"]',
                'button[aria-label*="Options"]',
                'button[aria-label*="More"]',
                'button:has(svg[class*="trash"])',
            ]

            for selector in delete_selectors:
                btn = self.page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)

                    # Look for delete option in menu
                    if "Options" in selector or "More" in selector:
                        delete_option_selectors = [
                            'button:has-text("Delete")',
                            '[role="menuitem"]:has-text("Delete")',
                        ]

                        for del_sel in delete_option_selectors:
                            del_btn = self.page.locator(del_sel).first
                            if await del_btn.count() > 0:
                                await del_btn.click()
                                break

                    # Confirm deletion
                    confirm_selectors = [
                        'button:has-text("Delete")',
                        'button:has-text("Confirm")',
                        'button[aria-label="Confirm deletion"]',
                    ]

                    for conf_sel in confirm_selectors:
                        conf_btn = self.page.locator(conf_sel).last  # Often in modal
                        if await conf_btn.count() > 0 and await conf_btn.is_visible():
                            await conf_btn.click()
                            await asyncio.sleep(1)
                            logger.info("Conversation deleted")
                            return True

            logger.error("Delete button not found")
            return False

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False

    async def edit_message(self, message_index: int, new_content: str) -> bool:
        """Edit a previous message in the conversation

        Args:
            message_index: Index of the message to edit (0-based, user messages only)
            new_content: New content for the message

        Returns:
            True if edit was successful, False otherwise
        """
        if not self.page:
            await self.launch()

        try:
            # Find all user message elements
            user_message_selectors = [
                '[data-message-author-role="user"]',
                'div[class*="user-message"]',
                "div.group:has(div.text-right)",  # Some versions use this layout
            ]

            user_messages = None
            for selector in user_message_selectors:
                messages = self.page.locator(selector)
                count = await messages.count()
                if count > 0:
                    user_messages = messages
                    break

            if not user_messages:
                logger.error("No user messages found")
                return False

            # Check if index is valid
            message_count = await user_messages.count()
            if message_index < 0 or message_index >= message_count:
                logger.error(
                    f"Invalid message index: {message_index} (found {message_count} messages)"
                )
                return False

            # Get the specific message
            target_message = user_messages.nth(message_index)

            # Look for edit button
            edit_button_selectors = [
                'button[aria-label*="Edit"]',
                'button:has(svg[aria-label*="edit"])',
                'button:has(svg[class*="pencil"])',
            ]

            edit_button = None
            for selector in edit_button_selectors:
                btn = target_message.locator(selector).first
                if await btn.count() > 0:
                    edit_button = btn
                    break

            if not edit_button:
                # Try hovering to reveal edit button
                await target_message.hover()
                await asyncio.sleep(0.5)

                # Try again
                for selector in edit_button_selectors:
                    btn = target_message.locator(selector).first
                    if await btn.count() > 0:
                        edit_button = btn
                        break

            if not edit_button:
                logger.error("Edit button not found")
                return False

            # Click edit button
            await edit_button.click()
            await asyncio.sleep(0.5)

            # Find the edit textarea
            edit_textarea_selectors = [
                'textarea[aria-label*="Edit"]',
                "textarea.editing",
                "textarea:focus",  # Often the textarea gets focus
            ]

            edit_textarea = None
            for selector in edit_textarea_selectors:
                textarea = self.page.locator(selector).first
                if await textarea.count() > 0:
                    edit_textarea = textarea
                    break

            if not edit_textarea:
                logger.error("Edit textarea not found")
                return False

            # Clear and type new content
            await edit_textarea.clear()
            await edit_textarea.fill(new_content)

            # Submit the edit - usually Enter or a submit button
            submit_selectors = [
                'button[aria-label*="Save"]',
                'button[aria-label*="Submit"]',
                'button:has(svg[aria-label*="send"])',
            ]

            submitted = False
            for selector in submit_selectors:
                btn = self.page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    submitted = True
                    break

            if not submitted:
                # Try pressing Enter
                await edit_textarea.press("Enter")

            logger.info(f"Edited message at index {message_index}")
            return True

        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return False

    async def execute_batch_operations(self, operations: list[dict]) -> dict:
        """Execute multiple operations in sequence with comprehensive error handling

        Args:
            operations: List of operation dictionaries with format:
                {
                    "operation": "operation_name",
                    "args": {...},  # optional arguments
                    "continue_on_error": bool  # optional, default False
                }

        Returns:
            Dictionary with results for each operation and overall status
        """
        if not self.page:
            await self.launch()

        results = {
            "success": True,
            "operations": [],
            "total_operations": len(operations),
            "successful_operations": 0,
            "failed_operations": 0,
        }

        for i, op in enumerate(operations):
            operation_name = op.get("operation", "")
            args = op.get("args", {})
            continue_on_error = op.get("continue_on_error", False)

            op_result = {
                "index": i,
                "operation": operation_name,
                "success": False,
                "result": None,
                "error": None,
            }

            try:
                # Map operation names to methods
                if operation_name == "new_chat":
                    op_result["result"] = await self.new_chat()
                    op_result["success"] = True

                elif operation_name == "send_message":
                    message = args.get("message", "")
                    op_result["result"] = await self.send_message(message)
                    op_result["success"] = True

                elif operation_name == "send_and_get_response":
                    message = args.get("message", "")
                    timeout = args.get("timeout", 120)
                    op_result["result"] = await self.send_and_get_response(message, timeout)
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "get_last_response":
                    op_result["result"] = await self.get_last_response()
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "get_conversation":
                    op_result["result"] = await self.get_conversation()
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "select_model":
                    model = args.get("model", "")
                    op_result["result"] = await self.select_model(model)
                    op_result["success"] = op_result["result"]

                elif operation_name == "get_current_model":
                    op_result["result"] = await self.get_current_model()
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "toggle_search_mode":
                    enable = args.get("enable", True)
                    op_result["result"] = await self.toggle_search_mode(enable)
                    op_result["success"] = op_result["result"]

                elif operation_name == "toggle_browsing_mode":
                    enable = args.get("enable", True)
                    op_result["result"] = await self.toggle_browsing_mode(enable)
                    op_result["success"] = op_result["result"]

                elif operation_name == "upload_file":
                    file_path = args.get("file_path", "")
                    op_result["result"] = await self.upload_file(file_path)
                    op_result["success"] = op_result["result"]

                elif operation_name == "regenerate_response":
                    op_result["result"] = await self.regenerate_response()
                    op_result["success"] = op_result["result"]

                elif operation_name == "export_conversation":
                    format_type = args.get("format", "markdown")
                    op_result["result"] = await self.export_conversation(format_type)
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "save_conversation":
                    filename = args.get("filename")
                    format_type = args.get("format", "markdown")
                    op_result["result"] = await self.save_conversation(filename, format_type)
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "edit_message":
                    message_index = args.get("message_index", 0)
                    new_content = args.get("new_content", "")
                    op_result["result"] = await self.edit_message(message_index, new_content)
                    op_result["success"] = op_result["result"]

                elif operation_name == "list_conversations":
                    op_result["result"] = await self.list_conversations()
                    op_result["success"] = op_result["result"] is not None

                elif operation_name == "switch_conversation":
                    conversation_id = args.get("conversation_id", "")
                    op_result["result"] = await self.switch_conversation(conversation_id)
                    op_result["success"] = op_result["result"]

                elif operation_name == "delete_conversation":
                    conversation_id = args.get("conversation_id", "")
                    op_result["result"] = await self.delete_conversation(conversation_id)
                    op_result["success"] = op_result["result"]

                elif operation_name == "wait_for_response":
                    timeout = args.get("timeout", 30)
                    op_result["result"] = await self.wait_for_response(timeout)
                    op_result["success"] = op_result["result"]

                else:
                    op_result["error"] = f"Unknown operation: {operation_name}"
                    op_result["success"] = False

            except Exception as e:
                op_result["error"] = str(e)
                op_result["success"] = False
                logger.error(f"Operation {operation_name} failed: {e}")

            # Update counters
            if op_result["success"]:
                results["successful_operations"] += 1
            else:
                results["failed_operations"] += 1
                if not continue_on_error:
                    results["success"] = False

            results["operations"].append(op_result)

            # Stop if operation failed and continue_on_error is False
            if not op_result["success"] and not continue_on_error:
                results["success"] = False
                logger.warning(f"Batch operation stopped at index {i} due to error")
                break

        # Overall success if all operations succeeded or all failures had continue_on_error=True
        results["success"] = results["failed_operations"] == 0 or all(
            op.get("continue_on_error", False)
            for op in operations[: len(results["operations"])]
            if not results["operations"][operations.index(op)]["success"]
        )

        logger.info(
            f"Batch operations completed: {results['successful_operations']}/{results['total_operations']} successful"
        )
        return results


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
