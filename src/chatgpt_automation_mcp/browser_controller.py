"""
Browser-based ChatGPT controller using Playwright
"""

import asyncio
import logging
import os
import subprocess
import platform
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
                    # Use full URL with http:// prefix  
                    cdp_url = self.config.CDP_URL
                    if not cdp_url.startswith('http'):
                        cdp_url = f"http://{cdp_url}"
                    self.browser = await self.playwright.chromium.connect_over_cdp(
                        cdp_url
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
                    logger.warning(f"CDP connection failed: {e}")
                    
                    # Try to launch Chrome with debugging
                    if await self._launch_chrome_with_debugging():
                        # Wait a bit for Chrome to start
                        await asyncio.sleep(5)
                        
                        # Try CDP connection again
                        try:
                            logger.info("Retrying CDP connection...")
                            # Use full URL with http:// prefix  
                            cdp_url = self.config.CDP_URL
                            if not cdp_url.startswith('http'):
                                cdp_url = f"http://{cdp_url}"
                            self.browser = await self.playwright.chromium.connect_over_cdp(
                                cdp_url
                            )
                            # Get existing contexts instead of creating new one
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
                                    logger.info("Connected to existing ChatGPT tab after Chrome launch")
                                else:
                                    self.page = await self.context.new_page()
                                    logger.info("Created new tab in existing browser after Chrome launch")
                            else:
                                # No contexts, create one
                                self.context = await self.browser.new_context()
                                self.page = await self.context.new_page()
                                logger.info("Created new context in CDP browser after Chrome launch")
                            
                            logger.info("Successfully connected via CDP after launching Chrome")
                            self.is_cdp_connection = True
                        except Exception as retry_e:
                            logger.error(f"CDP retry failed: {retry_e}")
                            # Give up on CDP
                            self.browser = None
                            self.context = None
                            self.page = None
                    else:
                        # Fall through to regular launch
                        self.browser = None
                        self.context = None
                        self.page = None
            
            # Regular launch if CDP not used or failed
            if not self.browser and not self.config.USE_CDP:
                # Only launch Chromium if CDP is explicitly disabled
                # Otherwise fail - Chromium won't work with Cloudflare
                logger.error("CDP connection required for ChatGPT automation (Cloudflare protection)")
                raise Exception("Cannot connect to Chrome. Please ensure Chrome is running or CDP is configured correctly.")

            # Check if we have a browser connection
            if not self.browser:
                raise Exception("Failed to establish browser connection. Chrome with debugging port is required.")
            
            # Navigate to ChatGPT only if not already there
            current_url = self.page.url if self.page else ""
            if "chatgpt.com" not in current_url and "chat.openai.com" not in current_url:
                logger.info("Navigating to ChatGPT...")
                await self.page.goto(
                    "https://chatgpt.com", wait_until="networkidle", timeout=60000
                )
                # Wait for theme to be applied - check for dark mode class on html element
                await self.page.wait_for_function(
                    """() => {
                        const html = document.querySelector('html');
                        return html && (html.classList.contains('dark') || html.classList.contains('light'));
                    }""",
                    timeout=5000
                )
            else:
                logger.info(f"Already on ChatGPT: {current_url}")

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

            # For critical browser launch failures, don't retry automatically
            # to avoid infinite loops
            logger.error("Browser launch failed. Not retrying to avoid loops.")
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

    async def _launch_chrome_with_debugging(self) -> bool:
        """Launch Chrome with debugging port enabled"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            elif system == "Windows":
                chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            elif system == "Linux":
                chrome_path = "google-chrome"
            else:
                logger.error(f"Unsupported platform: {system}")
                return False
            
            # Check if Chrome is already running with debugging
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.config.CDP_URL}/json/version") as response:
                        if response.status == 200:
                            logger.info("Chrome is already running with debugging port")
                            return True
            except Exception:
                logger.info("Chrome not running with debugging port, will launch it")
            
            logger.info(f"Launching Chrome with debugging port on {system}")
            
            # Only close Chrome if it's running WITHOUT debugging
            # First check if Chrome is running at all
            if system == "Darwin":
                check_chrome = '''
                tell application "System Events"
                    set chromeRunning to exists (processes where name is "Google Chrome")
                end tell
                return chromeRunning
                '''
                result = subprocess.run(['osascript', '-e', check_chrome], capture_output=True, text=True)
                chrome_running = result.stdout.strip() == "true"
                
                if chrome_running:
                    logger.info("Chrome is running without debugging port, closing it...")
                    # Use AppleScript to gracefully quit Chrome
                    quit_chrome = '''
                    tell application "Google Chrome"
                        quit
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', quit_chrome], capture_output=True)
                    await asyncio.sleep(2)  # Give Chrome time to close
            elif system == "Windows":
                # Check if Chrome is running
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], capture_output=True, text=True)
                chrome_running = "chrome.exe" in result.stdout
                
                if chrome_running:
                    logger.info("Chrome is running without debugging port, closing it...")
                    subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
                    await asyncio.sleep(2)
            elif system == "Linux":
                # Check if Chrome is running
                result = subprocess.run(['pgrep', '-f', 'chrome'], capture_output=True)
                chrome_running = result.returncode == 0
                
                if chrome_running:
                    logger.info("Chrome is running without debugging port, closing it...")
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                    await asyncio.sleep(2)
            
            # Launch Chrome with debugging port using default profile
            port = self.config.CDP_URL.split(':')[-1]
            cmd = [chrome_path, f"--remote-debugging-port={port}"]
            
            # Explicitly specify the default Chrome profile location
            if system == "Darwin":
                # macOS Chrome automation profile location
                user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome-Automation")
                cmd.extend(["--user-data-dir", user_data_dir])
            elif system == "Windows":
                # Windows default Chrome profile location
                user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
                cmd.extend(["--user-data-dir", user_data_dir])
            elif system == "Linux":
                # Linux default Chrome profile location
                user_data_dir = os.path.expanduser("~/.config/google-chrome")
                cmd.extend(["--user-data-dir", user_data_dir])
            
            logger.info(f"Launching Chrome with debugging port using profile: {user_data_dir}")
            
            # Launch Chrome with ChatGPT URL directly
            cmd.append("https://chatgpt.com")
            
            # Log the exact command being run
            logger.info(f"Running command: {' '.join(cmd)}")
            
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Chrome launched with debugging port")
            
            # Wait for Chrome to be ready
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch Chrome with debugging: {e}")
            return False

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
            # Wait for theme to be applied
            await self.page.wait_for_function(
                """() => {
                    const html = document.querySelector('html');
                    return html && (html.classList.contains('dark') || html.classList.contains('light'));
                }""",
                timeout=5000
            )

        # Wait for input to be ready and page to be interactive
        await self.page.wait_for_selector("#prompt-textarea", state="visible")
        
        # Wait for any animations to complete
        await self.page.wait_for_function(
            """() => !document.querySelector('body').classList.contains('loading')""",
            timeout=5000
        )
        
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
            # Primary method: Get all article elements (conversation messages)
            articles = await self.page.locator('main article').all()
            
            if not articles:
                # Fallback: Try other message selectors
                message_selectors = [
                    'div[data-message-author-role="assistant"]',
                    'div.group:has(div:has-text("ChatGPT"))',
                    'div.flex.flex-col:has(div:has-text("said:"))',
                ]
                
                for selector in message_selectors:
                    messages = await self.page.locator(selector).all()
                    if messages:
                        articles = messages
                        break
            
            if not articles:
                return None

            # Get the last article (should be assistant's response)
            last_article = articles[-1]

            # Extract text content
            text_content = await last_article.inner_text()

            # Clean up the text
            # Remove common prefixes
            prefixes_to_remove = [
                "ChatGPT said:",
                "ChatGPT",
                "GPT-4o said:",
                "GPT-4 said:",
                "o1 said:",
                "o3 said:",
                "said:"
            ]
            
            cleaned_text = text_content.strip()
            for prefix in prefixes_to_remove:
                if cleaned_text.startswith(prefix):
                    cleaned_text = cleaned_text[len(prefix):].strip()
                    break
            
            # Also check for "Do you like this personality?" and similar suffixes
            # These are sometimes added by ChatGPT
            suffixes_to_remove = [
                "Do you like this personality?",
                "Was this response helpful?",
                "Is this what you were looking for?"
            ]
            
            for suffix in suffixes_to_remove:
                if cleaned_text.endswith(suffix):
                    cleaned_text = cleaned_text[:-len(suffix)].strip()

            return cleaned_text

        except Exception as e:
            logger.error(f"Failed to get last response: {e}")
            return None

    async def get_conversation(self) -> list[dict[str, str]]:
        """Get the full conversation history"""
        if not self.page:
            return []

        try:
            conversation = []
            
            # Get all articles (messages)
            articles = await self.page.locator('main article').all()
            
            if not articles:
                # Fallback selectors
                articles = await self.page.locator('div[data-message-author-role]').all()
            
            # Process each article
            for article in articles:
                text = await article.inner_text()
                
                # Determine role based on content
                role = "assistant"
                if "You said:" in text or text.startswith("You said:"):
                    role = "user"
                    text = text.replace("You said:", "").strip()
                elif any(prefix in text for prefix in ["ChatGPT said:", "GPT-4o said:", "said:"]):
                    role = "assistant"
                    # Remove the prefix
                    for prefix in ["ChatGPT said:", "GPT-4o said:", "GPT-4 said:", "o1 said:", "o3 said:", "said:"]:
                        if text.startswith(prefix):
                            text = text[len(prefix):].strip()
                            break
                
                # Clean up common suffixes
                suffixes_to_remove = [
                    "Do you like this personality?",
                    "Was this response helpful?",
                    "Is this what you were looking for?"
                ]
                
                for suffix in suffixes_to_remove:
                    if text.endswith(suffix):
                        text = text[:-len(suffix)].strip()
                
                if text:  # Only add non-empty messages
                    conversation.append({"role": role, "content": text})

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
        # Primary method: Look for the model switcher button
        try:
            # The model switcher has a specific test ID
            model_button = self.page.locator('[data-testid="model-switcher-dropdown-button"]').first
            if await model_button.count() > 0 and await model_button.is_visible():
                text = await model_button.text_content()
                if text:
                    # Clean up the text - remove "ChatGPT" prefix if present
                    text = text.strip()
                    if text.startswith("ChatGPT "):
                        text = text[8:]  # Remove "ChatGPT " prefix
                    return text
        except Exception:
            pass
            
        # Fallback: Look for model info in header buttons
        try:
            header_buttons = self.page.locator('header button[aria-label*="Model selector"]')
            if await header_buttons.count() > 0:
                button = header_buttons.first
                if await button.is_visible():
                    text = await button.text_content()
                    if text:
                        # Extract model from text like "ChatGPT 4o"
                        parts = text.strip().split()
                        if len(parts) > 1:
                            return parts[-1]  # Return last part (the model)
        except Exception:
            pass
        
        # Additional fallback: Look for any button with model names
        model_selectors = [
            'button:has-text("4o")',
            'button:has-text("o1")',
            'button:has-text("o3")',
            'button:has-text("GPT-4")',
            'button:has-text("GPT-4.5")',
        ]
        
        for selector in model_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    text = await element.text_content()
                    if text:
                        # Extract just the model name
                        for model in ["4o", "o1", "o3", "GPT-4.5", "GPT-4"]:
                            if model in text:
                                return model
            except Exception:
                continue
        
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
        
        # Special handling for GPT-4o (it's the default and might not be selectable)
        if model.lower() in ["gpt-4o", "4o"] and (current and "4o" in current.lower()):
            logger.info("GPT-4o is already the default model")
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
            # Try the specific selector we know works
            try:
                model_button = self.page.locator('[data-testid="model-switcher-dropdown-button"]').first
                if await model_button.count() > 0 and await model_button.is_visible():
                    await model_button.click()
                    await asyncio.sleep(0.5)
                    clicked = True
                    logger.info("Opened model picker with data-testid selector")
            except Exception:
                pass
                
        if not clicked:
            logger.warning("Could not find model picker")
            return False

        # Wait for menu to open - look for menuitem elements
        try:
            await self.page.wait_for_selector(
                'div[role="menuitem"]',
                state="visible",
                timeout=5000,
            )
        except Exception:
            logger.warning("Model menu did not appear")
            return False
            
        await asyncio.sleep(0.5)  # Small delay for animation

        # Model name mapping based on actual ChatGPT UI (Jan 2025)
        model_map = {
            # Main models
            "gpt-4o": ["GPT-4o", "gpt-4o", "GPT 4o", "4o"],  # Default model
            "4o": ["GPT-4o", "gpt-4o", "GPT 4o"],  # Allow "4o" as shorthand
            "o3": ["o3", "O3"],  # Advanced reasoning
            "o3-pro": ["o3-pro", "O3-pro", "o3 pro"],  # Best at reasoning
            "o4-mini": ["o4-mini", "O4-mini", "o4 mini"],  # Fastest at advanced reasoning
            "o4-mini-high": ["o4-mini-high", "O4-mini-high", "o4 mini high"],  # Great at coding and visual reasoning
            # More models menu
            "gpt-4.5": ["GPT-4.5", "gpt-4.5", "GPT 4.5"],  # Research preview
            "gpt-4.1": ["GPT-4.1", "gpt-4.1", "GPT 4.1"],  # Great for quick coding and analysis
            "gpt-4.1-mini": ["GPT-4.1-mini", "gpt-4.1-mini", "GPT 4.1 mini"],  # Faster for everyday tasks
        }

        # Get possible UI texts for the model
        ui_models = model_map.get(model.lower(), [model])
        if not isinstance(ui_models, list):
            ui_models = [ui_models]

        # Check if this is a model that requires "More models" submenu
        more_models = ["gpt-4.5", "gpt-4.1", "gpt-4.1-mini"]
        needs_more_menu = any(m in model.lower() for m in more_models)
        
        if needs_more_menu:
            # First click "More models" option
            try:
                # Look for More models item - it might be a div with role="menuitem"
                more_button_selectors = [
                    'div[role="menuitem"]:has-text("More models")',
                    'div:has-text("More models"):not(:has(div))',
                    '[role="menuitem"]:has-text("More models")',
                    'button:has-text("More models")',
                ]
                
                more_clicked = False
                for selector in more_button_selectors:
                    more_button = self.page.locator(selector).first
                    if await more_button.count() > 0 and await more_button.is_visible():
                        # Try hovering first (some menus require hover)
                        await more_button.hover()
                        await asyncio.sleep(0.3)
                        
                        # Now click
                        await more_button.click()
                        await asyncio.sleep(1.0)  # Wait for submenu animation
                        more_clicked = True
                        logger.info(f"Clicked 'More models' submenu with selector: {selector}")
                        break
                
                if not more_clicked:
                    logger.warning("'More models' menu not found, trying direct selection")
                    # Don't fail immediately - try to find the model anyway
            except Exception as e:
                logger.error(f"Failed to click 'More models': {e}")

        # Try to find and click the model option
        option_selectors = [
            'div[role="menuitem"]',
            'div[role="option"]',
            'button[role="menuitem"]',
            'li[role="option"]',
            "[data-radix-menu-item]",
            # Additional selectors for submenu items
            'div:not(:has(div))',  # Leaf div nodes
            'span:not(:has(span))',  # Leaf span nodes
        ]

        for ui_model in ui_models:
            for selector in option_selectors:
                try:
                    # Try exact match first
                    if selector in ['div:not(:has(div))', 'span:not(:has(span))']:
                        # For leaf nodes, use text-is for exact match
                        option = self.page.locator(f'{selector}:text-is("{ui_model}")').first
                    else:
                        # For other selectors, use has-text
                        option = self.page.locator(f'{selector}:has-text("{ui_model}")').first
                    
                    if await option.count() > 0 and await option.is_visible():
                        # For More models submenu items, might need to wait for them to be clickable
                        if needs_more_menu:
                            await option.hover()
                            await asyncio.sleep(0.2)
                        
                        await option.click()
                        await asyncio.sleep(1.5)  # Increased wait for selection to apply

                        # Verify selection with retry
                        for retry in range(3):
                            await asyncio.sleep(0.5)
                            new_model = await self.get_current_model()
                            if new_model:
                                # Check if the selected model matches (handle variations)
                                model_matched = False
                                if ui_model.lower() in new_model.lower():
                                    model_matched = True
                                elif model.lower() in new_model.lower():
                                    model_matched = True
                                # Special case for GPT models
                                elif "gpt" in model.lower() and "gpt" in new_model.lower():
                                    # Extract version numbers and compare
                                    import re
                                    model_version = re.search(r'[\d.]+', model)
                                    new_version = re.search(r'[\d.]+', new_model)
                                    if model_version and new_version and model_version.group() == new_version.group():
                                        model_matched = True
                                
                                if model_matched:
                                    logger.info(f"Successfully selected model: {new_model}")
                                    return True
                            
                            # If not matched and still retrying, wait a bit more
                            if retry < 2:
                                logger.debug(f"Model not yet updated, retrying... (attempt {retry + 1}/3)")
                except Exception as e:
                    logger.debug(f"Failed with selector {selector}: {e}")
                    continue

        # If we still haven't found it, try one more time with a broader search
        if needs_more_menu:
            # Sometimes the submenu needs a second click or the items are loaded dynamically
            try:
                # Look for any element containing the model text
                all_elements = self.page.locator(f'*:has-text("{model}")')
                count = await all_elements.count()
                logger.debug(f"Found {count} elements containing '{model}'")
                
                for i in range(min(count, 5)):  # Check first 5 matches
                    elem = all_elements.nth(i)
                    if await elem.is_visible():
                        tag = await elem.evaluate("el => el.tagName")
                        parent_tag = await elem.evaluate("el => el.parentElement ? el.parentElement.tagName : 'none'")
                        text = await elem.text_content()
                        logger.debug(f"  Element {i}: <{tag}> in <{parent_tag}>, text: '{text.strip()}'")
                        
                        # Try clicking if it looks like a menu item
                        if tag.lower() in ['div', 'button', 'li', 'span'] and model in text:
                            await elem.click()
                            await asyncio.sleep(1.0)
                            
                            # Final check
                            new_model = await self.get_current_model()
                            if new_model and (model.lower() in new_model.lower() or 
                                            any(variant.lower() in new_model.lower() for variant in ui_models)):
                                logger.info(f"Successfully selected model via fallback: {new_model}")
                                return True
            except Exception as e:
                logger.debug(f"Fallback search failed: {e}")
        
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
    
    async def is_sidebar_open(self) -> bool:
        """Check if the sidebar is currently open"""
        try:
            # Check for sidebar state - look for the close button which only appears when open
            close_button = self.page.locator('[data-testid="close-sidebar-button"]').first
            if await close_button.count() > 0 and await close_button.is_visible():
                return True
            
            # Alternative: check aria-expanded attribute
            sidebar_button = self.page.locator('[aria-controls="stage-slideover-sidebar"]').first
            if await sidebar_button.count() > 0:
                aria_expanded = await sidebar_button.get_attribute('aria-expanded')
                return aria_expanded == 'true'
            
            return False
        except Exception:
            return False
    
    async def toggle_sidebar(self, open: bool = True) -> bool:
        """Open or close the sidebar
        
        Args:
            open: True to open sidebar, False to close it
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_state = await self.is_sidebar_open()
            
            # If already in desired state, return success
            if current_state == open:
                logger.info(f"Sidebar already {'open' if open else 'closed'}")
                return True
            
            if open:
                # Look for open sidebar button
                open_button = self.page.locator('[aria-label="Open sidebar"]').first
                if await open_button.count() > 0 and await open_button.is_visible():
                    await open_button.click()
                    await asyncio.sleep(1.0)  # Increased wait for animation
                    logger.info("Opened sidebar")
                    return True
            else:
                # Look for close sidebar button
                close_button = self.page.locator('[data-testid="close-sidebar-button"]').first
                if await close_button.count() > 0 and await close_button.is_visible():
                    await close_button.click()
                    await asyncio.sleep(1.0)  # Increased wait for animation
                    logger.info("Closed sidebar")
                    return True
            
            logger.warning(f"Could not {'open' if open else 'close'} sidebar")
            return False
            
        except Exception as e:
            logger.error(f"Failed to toggle sidebar: {e}")
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
        """Toggle web search mode via Tools menu"""
        if not self.page:
            await self.launch()

        try:
            # First, open the Tools menu - need to be more specific with selector
            # Based on error, the button has id="system-hint-button" and aria-label="Choose tool"
            tools_button = self.page.locator('button[aria-label="Choose tool"]').first
            if await tools_button.count() == 0:
                # Try alternative selectors
                tools_button = self.page.locator('#system-hint-button').first
                if await tools_button.count() == 0:
                    tools_button = self.page.locator('button.composer-btn:has-text("Tools")').first
                
            if await tools_button.count() > 0 and await tools_button.is_visible():
                # Force click to bypass interception
                await tools_button.click(force=True)
                await asyncio.sleep(0.5)  # Wait for menu
                
                # Now find Web search option - it's a div in the menu
                search_option = self.page.locator('div[role="menu"] div:has-text("Web search")').first
                if await search_option.count() == 0:
                    # Try more specific selector
                    search_option = self.page.locator('div:text-is("Web search")').first
                    
                if await search_option.count() > 0 and await search_option.is_visible():
                    # Web search is a toggle - clicking it enables/disables
                    await search_option.click()
                    # Wait for menu to close and UI to update
                    await self.page.wait_for_selector(
                        'div[role="menu"]',
                        state="hidden",
                        timeout=3000
                    )
                    # Small wait for any remaining transitions
                    await self.page.wait_for_timeout(500)
                    logger.info(f"Toggled web search mode")
                    return True
                else:
                    logger.warning("Web search option not found in Tools menu")
                    return False
            else:
                logger.warning("Tools button not found")
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
    
    async def enable_deep_research(self) -> bool:
        """Enable Deep Research mode via Tools menu
        
        Note: Deep Research has a monthly quota (250/month)
        """
        if not self.page:
            await self.launch()

        try:
            # First, open the Tools menu - use specific selector
            tools_button = self.page.locator('button[aria-label="Choose tool"]').first
            if await tools_button.count() == 0:
                tools_button = self.page.locator('#system-hint-button').first
                
            if await tools_button.count() > 0 and await tools_button.is_visible():
                await tools_button.click(force=True)
                await asyncio.sleep(0.5)  # Wait for menu
                
                # Now find Deep research option - use the exact selector that works
                research_option = self.page.locator('div:text-is("Deep research")').first
                    
                if await research_option.count() > 0 and await research_option.is_visible():
                    await research_option.click()
                    # Wait for Deep Research UI to appear
                    try:
                        await self.page.wait_for_selector(
                            'text=/What are you researching/i',
                            state="visible",
                            timeout=5000
                        )
                    except Exception:
                        # Alternative: wait for Sources button
                        await self.page.wait_for_selector(
                            'button:has-text("Sources")',
                            state="visible", 
                            timeout=5000
                        )
                    logger.info("Selected Deep Research mode")
                    return True
                else:
                    # Fallback to less specific selector
                    research_option = self.page.locator('div[role="menu"] div:has-text("Deep research")').first
                    if await research_option.count() > 0 and await research_option.is_visible():
                        await research_option.click()
                        # Wait for Deep Research UI to appear
                        try:
                            await self.page.wait_for_selector(
                                'text=/What are you researching/i',
                                state="visible",
                                timeout=5000
                            )
                        except Exception:
                            # Alternative: wait for Sources button
                            await self.page.wait_for_selector(
                                'button:has-text("Sources")',
                                state="visible", 
                                timeout=5000
                            )
                        logger.info("Selected Deep Research mode")
                        return True
                    else:
                        logger.warning("Deep research option not found in Tools menu")
                        return False
            else:
                logger.warning("Tools button not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to enable deep research: {e}")
            return False
    
    async def get_quota_remaining(self, mode: str = "deep_research") -> int | None:
        """Get remaining quota for Deep Research or other limited modes
        
        Args:
            mode: The mode to check quota for ("deep_research", etc.)
            
        Returns:
            Number of remaining uses, or None if not found
        """
        if not self.page:
            await self.launch()
            
        try:
            # Open Tools menu
            tools_button = self.page.locator('button[aria-label="Choose tool"]').first
            if await tools_button.count() == 0:
                tools_button = self.page.locator('#system-hint-button').first
                
            if await tools_button.count() > 0 and await tools_button.is_visible():
                await tools_button.click(force=True)
                await asyncio.sleep(0.5)
                
                # Look for the quota text - appears as tooltip or in menu
                if mode == "deep_research":
                    # Hover over Deep research to see tooltip
                    research_option = self.page.locator('div[role="menu"] div:has-text("Deep research")').first
                    if await research_option.count() == 0:
                        research_option = self.page.locator('div:text-is("Deep research")').first
                        
                    if await research_option.count() > 0:
                        await research_option.hover()
                        await asyncio.sleep(0.5)
                        
                        # Look for tooltip with quota info (e.g. "248 left")
                        quota_text = self.page.locator('[role="tooltip"]:has-text("left")').first
                        if await quota_text.count() == 0:
                            # Try looking for text near Deep research
                            quota_text = self.page.locator('div:has-text("left"):near(div:has-text("Deep research"))').first
                            
                        if await quota_text.count() > 0:
                            text = await quota_text.text_content()
                            # Extract number from text like "248 left"
                            import re
                            match = re.search(r'(\d+)\s*left', text)
                            if match:
                                return int(match.group(1))
                
                # Close menu by pressing Escape
                await self.page.keyboard.press("Escape")
                
        except Exception as e:
            logger.error(f"Failed to get quota: {e}")
            
        return None

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
            # First, check if we have an assistant response to regenerate
            articles = await self.page.locator('main article').all()
            if len(articles) < 2:
                logger.warning("No assistant response to regenerate")
                return False
            
            # Get the last article (should be assistant's response)
            last_article = articles[-1]
            text = await last_article.inner_text()
            
            # Verify it's an assistant message
            if "You said:" in text:
                logger.warning("Last message is from user, cannot regenerate")
                return False
            
            # In the new UI, regenerate is in the model dropdown menu
            # Click the model selector dropdown
            model_button = self.page.locator('[data-testid="model-switcher-dropdown-button"]').first
            if await model_button.count() == 0:
                # Fallback selector
                model_button = self.page.locator('header button[aria-label*="Model selector"]').first
            
            if await model_button.count() > 0 and await model_button.is_visible():
                await model_button.click()
                await asyncio.sleep(0.5)  # Wait for menu to open
                
                # Look for "Try again" option in the dropdown
                try_again_selectors = [
                    'button:has-text("Try again")',
                    'div[role="menuitem"]:has-text("Try again")',
                    '[role="menuitem"]:has-text("Try again")',
                    'button span:has-text("Try again")',
                ]
                
                for selector in try_again_selectors:
                    try_again = self.page.locator(selector).first
                    if await try_again.count() > 0 and await try_again.is_visible():
                        await try_again.click()
                        logger.info("Clicked 'Try again' to regenerate response")
                        
                        # Wait a bit for the UI to stabilize
                        # Note: Regeneration can cause the sidebar to flicker
                        await asyncio.sleep(1)
                        
                        # Close any open dropdowns to prevent UI issues
                        await self.page.keyboard.press("Escape")
                        
                        return True
                
                # If not found, close the dropdown
                await self.page.keyboard.press("Escape")
            
            logger.warning("Could not find regenerate option in model dropdown")
            return False

        except Exception as e:
            logger.error(f"Failed to regenerate response: {e}")
            return False
    
    async def _is_responding(self) -> bool:
        """Check if ChatGPT is currently generating a response"""
        try:
            # Check for thinking indicators
            thinking_selectors = [
                '[data-testid="thinking-indicator"]',
                ".animate-pulse",
                'div:has-text("Thinking")',
                'button:has-text("Stop generating")',
            ]
            
            for selector in thinking_selectors:
                if await self.page.locator(selector).count() > 0:
                    return True
            
            return False
        except Exception:
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
                from datetime import datetime
                
                # Add metadata
                export_data = {
                    "model": await self.get_current_model() or "Unknown",
                    "timestamp": datetime.now().isoformat(),
                    "messages": conversation
                }
                return json.dumps(export_data, indent=2)

            elif format == "markdown":
                # Convert to markdown format
                from datetime import datetime
                
                md_lines = []
                md_lines.append("# ChatGPT Conversation")
                
                # Get current model
                model = await self.get_current_model() or "Unknown"
                md_lines.append(f"\n**Model**: {model}")
                md_lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                # Add messages
                for msg in conversation:
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
            # Ensure sidebar is open to see conversations
            await self.toggle_sidebar(open=True)
            
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
                        '[data-testid^="history-item-"]',  # New pattern with test IDs
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
            # Ensure sidebar is open
            await self.toggle_sidebar(open=True)
            
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
                            f'[data-testid^="history-item-"]:has-text("{conv["title"]}")',
                            f'[data-testid="conversation-item"]:has-text("{conv["title"]}")',
                            f'div[role="button"]:has-text("{conv["title"]}")',
                        ]

                        for selector in item_selectors:
                            item = self.page.locator(selector).first
                            if await item.count() > 0:
                                await item.click()
                                await asyncio.sleep(1)  # Wait for navigation
                                logger.info(f"Switched to conversation: {conv['title']}")
                                
                                # Close sidebar after switching (optional)
                                await self.toggle_sidebar(open=False)
                                return True
            else:
                # Direct navigation by ID
                await self.page.goto(f"https://chatgpt.com/c/{conversation_id}")
                await self.page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1)

                # Verify we're in the right conversation
                if await self.is_ready():
                    logger.info(f"Switched to conversation: {conversation_id}")
                    # Close sidebar after switching (optional)
                    await self.toggle_sidebar(open=False)
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

            # The delete option might be in the header
            # Look for conversation options button in header
            options_button = self.page.locator('[data-testid="conversation-options-button"]').first
            if await options_button.count() == 0:
                # Fallback selectors
                options_selectors = [
                    'button[aria-label="Open conversation options"]',
                    'header button[aria-label*="Options"]',
                    'header button[aria-label*="More"]',
                ]
                
                for selector in options_selectors:
                    btn = self.page.locator(selector).first
                    if await btn.count() > 0 and await btn.is_visible():
                        options_button = btn
                        break
            
            if await options_button.count() > 0 and await options_button.is_visible():
                await options_button.click()
                await asyncio.sleep(0.5)
                
                # Look for delete option in menu
                delete_option_selectors = [
                    'button:has-text("Delete")',
                    '[role="menuitem"]:has-text("Delete")',
                    'div[role="menuitem"]:has-text("Delete")',
                ]
                
                for del_sel in delete_option_selectors:
                    del_btn = self.page.locator(del_sel).first
                    if await del_btn.count() > 0 and await del_btn.is_visible():
                        await del_btn.click()
                        await asyncio.sleep(0.5)
                        
                        # Confirm deletion
                        confirm_selectors = [
                            'button:has-text("Delete")',
                            'button:has-text("Confirm")',
                            'button[aria-label="Confirm deletion"]',
                            '[role="dialog"] button:has-text("Delete")',
                        ]
                        
                        for conf_sel in confirm_selectors:
                            conf_btn = self.page.locator(conf_sel).last  # Often in modal
                            if await conf_btn.count() > 0 and await conf_btn.is_visible():
                                await conf_btn.click()
                                await asyncio.sleep(1)
                                logger.info("Conversation deleted")
                                return True
                        
                        break
            
            logger.error("Could not find delete option")
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
            # Get all articles (messages)
            articles = await self.page.locator('main article').all()
            
            # Filter for user messages
            user_articles = []
            for article in articles:
                text = await article.inner_text()
                if "You said:" in text or text.startswith("You said:"):
                    user_articles.append(article)
            
            if not user_articles:
                logger.error("No user messages found")
                return False
            
            # Check if index is valid
            if message_index < 0 or message_index >= len(user_articles):
                logger.error(
                    f"Invalid message index: {message_index} (found {len(user_articles)} user messages)"
                )
                return False
            
            # Get the specific message
            target_message = user_articles[message_index]
            
            # Hover to reveal edit button
            await target_message.hover()
            await asyncio.sleep(0.5)
            
            # Look for edit button with the specific aria-label we found
            edit_button = target_message.locator('button[aria-label="Edit message"]').first
            
            if await edit_button.count() == 0 or not await edit_button.is_visible():
                # Try alternative selectors
                edit_button_selectors = [
                    'button[aria-label*="Edit"]',
                    'button:has(svg[class*="pencil"])',
                ]
                
                for selector in edit_button_selectors:
                    btn = target_message.locator(selector).first
                    if await btn.count() > 0 and await btn.is_visible():
                        edit_button = btn
                        break
                else:
                    logger.error("Edit button not found after hovering")
                    return False
            
            # Click edit button
            await edit_button.click()
            await asyncio.sleep(0.5)
            
            # Find the edit textarea - it should appear in place of the message
            edit_textarea = target_message.locator('textarea').first
            
            if await edit_textarea.count() == 0:
                # Try global search
                edit_textarea = self.page.locator('textarea:focus').first
                
            if await edit_textarea.count() == 0:
                logger.error("Edit textarea not found")
                return False
            
            # Clear and type new content
            await edit_textarea.clear()
            await edit_textarea.fill(new_content)
            
            # Submit the edit - usually Enter
            await edit_textarea.press("Enter")
            
            # Wait for the edit to process
            await asyncio.sleep(1)
            
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
