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

from .animation_config import get_delay

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
                        # noinspection HttpUrlsUsage
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
                        # No contexts found - this shouldn't happen with CDP
                        # The browser should have at least one default context
                        logger.error("No contexts found in CDP browser - this is unexpected")
                        raise Exception("CDP browser has no contexts. Please ensure Chrome is properly launched.")
                    
                    logger.info("Successfully connected via CDP")
                    self.is_cdp_connection = True
                except Exception as e:
                    logger.warning(f"CDP connection failed: {e}")
                    
                    # Try to launch Chrome with debugging
                    if await self._launch_chrome_with_debugging():
                        # Wait a bit for Chrome to start
                        await asyncio.sleep(get_delay("browser_startup"))
                        
                        # Try CDP connection again
                        try:
                            logger.info("Retrying CDP connection...")
                            # Use full URL with http:// prefix  
                            cdp_url = self.config.CDP_URL
                            if not cdp_url.startswith('http'):
                                # noinspection HttpUrlsUsage
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
                                # No contexts found - this shouldn't happen with CDP
                                logger.error("No contexts found in CDP browser after Chrome launch")
                                raise Exception("CDP browser has no contexts after launch. Please check Chrome startup.")
                            
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
            
            # Fallback handling if CDP failed
            if not self.browser:
                if self.config.USE_CDP:
                    # CDP required but failed - this is an error
                    logger.error("CDP connection required for ChatGPT automation (Cloudflare protection)")
                    raise Exception("Cannot connect to Chrome. Please ensure Chrome is running or CDP is configured correctly.")
                else:
                    # CDP explicitly disabled - use Playwright launch (won't work with ChatGPT but useful for other testing)
                    logger.info("Using Playwright browser launch (CDP disabled - note: won't work with ChatGPT)")
                    await self._launch_playwright_browser()
            
            # Navigate to ChatGPT only if not already there
            current_url = self.page.url if self.page else ""
            if "chatgpt.com" not in current_url and "chat.openai.com" not in current_url:
                logger.info("Navigating to ChatGPT...")
                # Use more lenient wait strategy in test mode
                wait_until = "domcontentloaded" if self.config.TEST_MODE else "networkidle"
                timeout = 30000 if self.config.TEST_MODE else 60000
                await self.page.goto(
                    "https://chatgpt.com", wait_until=wait_until, timeout=timeout
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
            
            # Ensure we're on the main chat interface, not the intro page
            await asyncio.sleep(1)  # Brief wait for page to load
            try:
                # Check if we're on intro page by looking for "Introducing" text
                page_title = await self.page.title()
                current_url = self.page.url
                
                if "Introducing" in page_title or current_url == "https://chatgpt.com/" or "/discovery" in current_url:
                    logger.info("On intro/landing page, starting new chat...")
                    # Don't use /c/new directly as it may fail - use the new chat button instead
                    try:
                        # Method 1: Click the "Ask anything" input to start a chat
                        ask_input = self.page.locator('input[placeholder*="Ask"]').first
                        if await ask_input.count() > 0:
                            await ask_input.click()
                            await ask_input.fill("Hello")
                            await ask_input.press("Enter")
                            await asyncio.sleep(3)
                            logger.info("Started chat via input field")
                        else:
                            # Method 2: Try the New chat button in sidebar
                            await self.new_chat()
                    except Exception as e:
                        logger.warning(f"Could not start new chat: {e}")
                        # Fallback: Just navigate to base URL
                        await self.page.goto("https://chatgpt.com", wait_until="networkidle", timeout=30000)
                    
                # Close sidebar if it's open to prevent blocking interactions
                if await self.is_sidebar_open():
                    logger.info("Closing sidebar to prevent UI blocking...")
                    await self.toggle_sidebar(open=False)
                    
            except Exception as e:
                logger.debug(f"Could not check/navigate from intro page: {e}")

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
                    await asyncio.sleep(get_delay("browser_close"))  # Give Chrome time to close
            elif system == "Windows":
                # Check if Chrome is running
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], capture_output=True, text=True)
                chrome_running = "chrome.exe" in result.stdout
                
                if chrome_running:
                    logger.info("Chrome is running without debugging port, closing it...")
                    subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
                    await asyncio.sleep(get_delay("browser_close"))
            elif system == "Linux":
                # Check if Chrome is running
                result = subprocess.run(['pgrep', '-f', 'chrome'], capture_output=True)
                chrome_running = result.returncode == 0
                
                if chrome_running:
                    logger.info("Chrome is running without debugging port, closing it...")
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                    await asyncio.sleep(get_delay("browser_close"))
            
            # Launch Chrome with debugging port using default profile
            port = self.config.CDP_URL.split(':')[-1]
            
            # Explicitly specify the default Chrome profile location
            if system == "Darwin":
                # macOS Chrome automation profile location
                user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome-Automation")
                # Use shell command to handle spaces properly
                cmd = f'"{chrome_path}" --remote-debugging-port={port} --user-data-dir="{user_data_dir}" "https://chatgpt.com"'
                use_shell = True
            else:
                # For Windows and Linux, use list format
                cmd = [chrome_path, f"--remote-debugging-port={port}"]
                if system == "Windows":
                    user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
                else:  # Linux
                    user_data_dir = os.path.expanduser("~/.config/google-chrome")
                cmd.extend(["--user-data-dir", user_data_dir])
                cmd.append("https://chatgpt.com")
                use_shell = False
            
            logger.info(f"Launching Chrome with debugging port using profile: {user_data_dir}")
            
            # Log the exact command being run
            logger.info(f"Running command: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
            
            process = subprocess.Popen(cmd, shell=use_shell, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Chrome launched with debugging port")
            
            # Wait for Chrome to be ready
            await asyncio.sleep(get_delay("browser_ready"))
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch Chrome with debugging: {e}")
            return False

    async def _launch_playwright_browser(self) -> None:
        """Launch browser using Playwright (for testing)"""
        try:
            logger.info("Launching Playwright browser...")
            
            # Configure browser launch arguments with anti-detection measures
            launch_args = [
                "--no-first-run",
                "--no-default-browser-check", 
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-blink-features=AutomationControlled",  # Critical for Cloudflare
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ]
            
            # Add user data directory for session persistence if not in test mode
            if not self.config.TEST_MODE and self.config.PERSIST_SESSION:
                user_data_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome-Automation"
                launch_args.append(f"--user-data-dir={user_data_dir}")
                logger.info(f"Using user data directory: {user_data_dir}")
            
            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.HEADLESS,
                args=launch_args,
                timeout=30000,  # 30 second timeout
            )
            
            # Create context with stealth options
            context_options = {
                "viewport": {"width": 1280, "height": 720},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "bypass_csp": True,  # Bypass content security policy
                "ignore_https_errors": True,  # Ignore certificate errors
                "java_script_enabled": True,
            }
            
            # Load session state if not in test mode
            if not self.config.TEST_MODE and self.config.PERSIST_SESSION:
                session_path = self.config.SESSION_DIR / f"{self.config.SESSION_NAME}.json"
                if session_path.exists():
                    context_options["storage_state"] = str(session_path)
                    logger.info(f"Loading session from: {session_path}")
            
            self.context = await self.browser.new_context(**context_options)
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set reasonable timeouts for testing
            self.page.set_default_timeout(30000)  # 30 seconds
            self.page.set_default_navigation_timeout(60000)  # 60 seconds
            
            logger.info("Playwright browser launched successfully")
            
        except Exception as e:
            logger.error(f"Failed to launch Playwright browser: {e}")
            # Clean up on failure
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            self.page = None
            self.context = None
            self.browser = None
            raise

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
        # Check if we're on landing page
        current_url = self.page.url
        
        # If on landing page or /c/new fails, start chat by typing
        if current_url == "https://chatgpt.com/" or "/discovery" in current_url:
            try:
                # Look for the "Ask anything" input field on landing page
                ask_input = self.page.locator('input[placeholder*="Ask"]').first
                if await ask_input.count() > 0:
                    logger.info("Starting chat from landing page input")
                    await ask_input.click()
                    await ask_input.fill("Hi")
                    await ask_input.press("Enter")
                    await asyncio.sleep(3)
                    return "new"
            except Exception as e:
                logger.debug(f"Could not use landing page input: {e}")
        
        # Try new chat button (but avoid /c/new which may fail)
        new_chat_selectors = [
            '[data-testid="create-new-chat-button"]',
            'button:has-text("New chat")',
            '[data-testid="new-chat-button"]',
        ]

        clicked = False
        for selector in new_chat_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    await element.click(force=True)
                    clicked = True
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue

        if not clicked:
            # Fallback: navigate to base and start typing
            logger.info("Using fallback - navigating to base URL")
            await self.page.goto("https://chatgpt.com/", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Try to start a chat
            try:
                textarea = self.page.locator("#prompt-textarea").first
                if await textarea.count() > 0:
                    await textarea.click()
                    await textarea.fill("Hello")
                    await textarea.press("Enter")
                    await asyncio.sleep(3)
                    return "new"
            except:
                # Last resort - use Ask input
                ask_input = self.page.locator('input[placeholder*="Ask"]').first
                if await ask_input.count() > 0:
                    await ask_input.click()
                    await ask_input.fill("Hello")
                    await ask_input.press("Enter")
                    await asyncio.sleep(3)
                    return "new"

        # Wait for input to be ready (if we clicked new chat button)
        try:
            await self.page.wait_for_selector("#prompt-textarea", state="visible", timeout=5000)
        except:
            pass
        
        # Wait for any animations to complete
        await self.page.wait_for_function(
            """() => !document.querySelector('body').classList.contains('loading')""",
            timeout=5000
        )
        
        return "New chat started"

    async def send_message(self, message: str, enable_web_search: bool = False, enable_deep_thinking: bool = False) -> str:
        """Send a message to ChatGPT with optional web search or deep thinking
        
        Args:
            message: The message to send
            enable_web_search: If True, adds "search the web" to trigger web search
            enable_deep_thinking: If True, adds "think deeply" to trigger deeper analysis
            
        Returns:
            Status message
        """
        if not self.page:
            await self.launch()

        try:
            # Modify message based on flags
            modified_message = message
            if enable_web_search:
                modified_message = f"{message}\n\n(Please search the web for this)"
                logger.debug("Added web search trigger to message")
            elif enable_deep_thinking:
                modified_message = f"{message}\n\n(Please think deeply about this)"
                logger.debug("Added deep thinking trigger to message")
            
            # Find and fill the textarea
            textarea = self.page.locator("#prompt-textarea")
            await textarea.wait_for(state="visible")
            await textarea.fill(modified_message)

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
        # Strategy: Wait for response action buttons (copy, like, etc.) to appear
        # These only show up when the response is complete
        
        # First check if "Stop generating" button exists (indicates active generation)
        stop_button = self.page.locator('button:has-text("Stop generating")').first
        generation_active = await stop_button.count() > 0 and await stop_button.is_visible()
        
        if generation_active:
            logger.debug("Generation is active, waiting for it to complete...")
            # Wait for the stop button to disappear
            try:
                await self.page.wait_for_selector(
                    'button:has-text("Stop generating")', 
                    state="hidden", 
                    timeout=timeout * 1000
                )
                logger.debug("Stop button disappeared, generation complete")
            except PlaywrightTimeout:
                logger.warning(f"Timeout waiting for generation to complete after {timeout}s")
                return False
        else:
            logger.debug("No active generation detected")
        
        # Now wait for response action buttons to appear - these indicate completion
        # Updated selectors based on actual ChatGPT UI (Dec 2024)
        completion_indicators = [
            'article button[aria-label="Copy"]',  # Copy button in response
            'article button[aria-label="Good response"]',  # Feedback button
            'article button[aria-label="Bad response"]',  # Feedback button  
            'article button[aria-label="Read aloud"]',  # Read aloud button
            'button:has-text("Copy")',  # Alternative: button with text
            'button:has-text("Good response")',  # Alternative: feedback
            'article:last-child button:has(img)',  # Last article with button icons
        ]
        
        # Wait for any completion indicator to appear
        response_complete = False
        for selector in completion_indicators:
            try:
                element = self.page.locator(selector).first
                # Quick check if already visible
                if await element.count() > 0 and await element.is_visible():
                    logger.debug(f"Response already complete, found: {selector}")
                    response_complete = True
                    break
                    
                # Wait for it to appear if not already visible
                await self.page.wait_for_selector(selector, state="visible", timeout=5000)
                logger.debug(f"Response complete, found indicator: {selector}")
                response_complete = True
                break
            except PlaywrightTimeout:
                continue
            except Exception as e:
                logger.debug(f"Error checking {selector}: {e}")
                continue
        
        if not response_complete:
            logger.warning("Could not confirm response completion via action buttons")
            # Fallback: wait a bit for any final rendering
            await asyncio.sleep(1)
        
        # Final wait for network idle to ensure everything is loaded
        try:
            await self.page.wait_for_load_state("networkidle", timeout=3000)
        except PlaywrightTimeout:
            logger.debug("Network idle timeout, but continuing")
        
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
                "GPT-5 said:",
                "GPT-5 Thinking said:",
                "GPT-5 Pro said:",
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
                elif any(prefix in text for prefix in ["ChatGPT said:", "GPT-5 said:", "said:"]):
                    role = "assistant"
                    # Remove the prefix
                    for prefix in ["ChatGPT said:", "GPT-5 said:", "GPT-5 Thinking said:", "GPT-5 Pro said:", "said:"]:
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
        # Primary method: Look for the model switcher button - try all visible instances
        try:
            # The model switcher has a specific test ID - there might be multiple, get the visible one
            model_buttons = self.page.locator('[data-testid="model-switcher-dropdown-button"]')
            count = await model_buttons.count()
            
            for i in range(count):
                model_button = model_buttons.nth(i)
                if await model_button.is_visible():
                    text = await model_button.text_content()
                    if text:
                        # Clean up the text - remove "ChatGPT " prefix if present
                        text = text.strip()
                        if text.startswith("ChatGPT "):
                            text = text[8:]  # Remove "ChatGPT " prefix
                        
                        # Normalize model names to full format (August 2025 UI update)
                        # UI now shows: "ChatGPT 5 Pro", "ChatGPT 5 Thinking mini", etc.
                        model_normalizations = {
                            # New UI format (August 2025)
                            "5": "GPT-5",
                            "5 Pro": "GPT-5 Pro", 
                            "5 Thinking": "GPT-5 Thinking",
                            "5 Thinking mini": "GPT-5 Thinking mini",
                            "5 Fast": "GPT-5 Fast",
                            "5 Auto": "GPT-5 Auto",
                            # Legacy models
                            "4o": "GPT-4o",
                            "4.5": "GPT-4.5",
                            "4.1": "GPT-4.1",
                            "4.1-mini": "GPT-4.1-mini", 
                            "o3": "o3",
                            "o3-pro": "o3-pro",
                            "o4-mini": "o4-mini",
                            # Handle "ChatGPT X" format (current UI)
                            "ChatGPT 5": "GPT-5",
                            "ChatGPT 5 Pro": "GPT-5 Pro",
                            "ChatGPT 5 Thinking": "GPT-5 Thinking", 
                            "ChatGPT 5 Thinking mini": "GPT-5 Thinking mini",
                            "ChatGPT 5 Fast": "GPT-5 Fast",
                            "ChatGPT 5 Auto": "GPT-5 Auto",
                            "ChatGPT 4o": "GPT-4o",
                            "ChatGPT o3": "o3",
                            "ChatGPT o4-mini": "o4-mini",
                        }
                        
                        # Try exact match first
                        if text in model_normalizations:
                            text = model_normalizations[text]
                        # If starts with ChatGPT, try without prefix
                        elif text.startswith("ChatGPT "):
                            without_prefix = text[8:]
                            if without_prefix in model_normalizations:
                                text = model_normalizations[without_prefix]
                        
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
        """Implementation of model selection logic using URL-based approach.
        
        This method uses direct URL navigation which is much more reliable than
        navigating the constantly-changing ChatGPT UI menus.
        """        
        # First check if we're already on the requested model
        current = await self.get_current_model()
        if current:
            current_lower = current.lower().replace("-", "").replace(" ", "").replace(".", "")
            model_lower = model.lower().replace("-", "").replace(" ", "").replace(".", "")
            
            # Check various matching patterns
            already_selected = (
                model_lower in current_lower or
                current_lower in model_lower or
                # Handle shorthand matches
                (model_lower == "gpt5" and current_lower == "gpt5") or
                (model_lower == "gpt5thinking" and "thinking" in current_lower) or
                (model_lower == "gpt5pro" and "pro" in current_lower) or
                (model_lower == "gpt45" and "gpt45" in current_lower) or
                (model_lower == "gpt41" and "gpt41" in current_lower and "mini" not in current_lower) or
                (model_lower == "gpt41mini" and "gpt41mini" in current_lower) or
                (model_lower == "o3" and current_lower == "o3" and "pro" not in current_lower) or
                (model_lower == "o3pro" and "o3pro" in current_lower) or
                (model_lower in ["o4mini", "o4-mini"] and "o4mini" in current_lower)
            )
            
            if already_selected:
                logger.info(f"Already using model: {current}")
                return True

        # URL-based model mapping - much more reliable than UI navigation
        # Based on testing August 2025: ChatGPT accepts these URL parameters
        url_model_map = {
            # GPT-5 models (current)
            "gpt-5": "gpt-5",
            "5": "gpt-5",
            "auto": "gpt-5",
            
            "gpt-5-thinking": "gpt-5-t",  # URL uses 't' not 'thinking'
            "gpt-5-t": "gpt-5-t", 
            "thinking": "gpt-5-t",
            
            "gpt-5-thinking-mini": "gpt-5-t-mini", 
            "gpt-5-t-mini": "gpt-5-t-mini",
            "thinking-mini": "gpt-5-t-mini",
            
            "gpt-5-pro": "gpt-5-pro",
            "5-pro": "gpt-5-pro", 
            "pro": "gpt-5-pro",
            
            # Legacy models we care about
            "gpt-4-1": "gpt-4-1",  # Uses dash not dot
            "gpt-4.1": "gpt-4-1",  # Convert dot to dash
            "4.1": "gpt-4-1",
            "4-1": "gpt-4-1",
            
            "o3": "o3",
            "o3-pro": "o3-pro",
            
            # Less important but supported
            "gpt-4o": "gpt-4o",
            "4o": "gpt-4o",
        }
        
        # Get the URL model parameter
        url_model = url_model_map.get(model.lower())
        if not url_model:
            logger.warning(f"Unsupported model: {model}. Supported: {list(url_model_map.keys())}")
            return False
        
        # Navigate directly to the model URL
        target_url = f"https://chatgpt.com/?model={url_model}"
        logger.debug(f"Navigating to: {target_url}")
        
        try:
            await self.page.goto(target_url, wait_until="domcontentloaded")
            await asyncio.sleep(get_delay("page_load"))
        except Exception as e:
            logger.error(f"Failed to navigate to model URL: {e}")
            return False
        
        # Verify the model was selected by checking the current model
        await asyncio.sleep(get_delay("model_verify"))
        new_model = await self.get_current_model()
        if new_model:
            # Normalize model names for comparison
            new_model_normalized = new_model.replace(" ", "").replace("-", "").lower()
            model_normalized = model.replace(" ", "").replace("-", "").lower()
            
            # Check if model changed successfully
            if model_normalized in new_model_normalized or new_model_normalized in model_normalized:
                logger.info(f"Successfully selected model via URL: {new_model}")
                return True
            # Special handling for shorthand names
            elif model.lower() == "5" and "gpt5" in new_model_normalized and "thinking" not in new_model_normalized and "pro" not in new_model_normalized:
                logger.info(f"Successfully selected base GPT-5 via URL: {new_model}")
                return True
            elif model.lower() == "thinking" and "thinking" in new_model_normalized:
                logger.info(f"Successfully selected GPT-5 Thinking via URL: {new_model}")
                return True
            elif model.lower() == "pro" and "pro" in new_model_normalized:
                logger.info(f"Successfully selected GPT-5 Pro via URL: {new_model}")
                return True
            elif model.lower() in ["o3"] and "o3" in new_model_normalized:
                logger.info(f"Successfully selected o3 via URL: {new_model}")
                return True
            elif model.lower() in ["4.1", "4-1", "gpt-4.1", "gpt-4-1"] and "41" in new_model_normalized:
                logger.info(f"Successfully selected GPT-4.1 via URL: {new_model}")
                return True
            else:
                logger.warning(f"URL-based model selection verification failed. Expected {model}, got {new_model}")
                return False
        else:
            logger.error(f"Could not verify model selection after URL navigation")
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
            # Multiple methods to detect sidebar state
            
            # Method 1: Check for close button (only visible when sidebar is open)
            close_button = self.page.locator('[data-testid="close-sidebar-button"]').first
            if await close_button.count() > 0 and await close_button.is_visible():
                return True
            
            # Method 2: Check aria-expanded attribute
            sidebar_button = self.page.locator('[aria-controls="stage-slideover-sidebar"]').first
            if await sidebar_button.count() > 0:
                aria_expanded = await sidebar_button.get_attribute('aria-expanded')
                if aria_expanded == 'true':
                    return True
            
            # Method 3: Check if sidebar panel is visible
            sidebar_panel = self.page.locator('[id="stage-slideover-sidebar"]').first
            if await sidebar_panel.count() > 0:
                # Check if it's actually visible (not hidden)
                is_visible = await sidebar_panel.is_visible()
                if is_visible:
                    return True
            
            # Method 4: Check for sidebar nav element
            sidebar_nav = self.page.locator('nav[aria-label="Chat history"]').first
            if await sidebar_nav.count() > 0 and await sidebar_nav.is_visible():
                return True
            
            return False
        except Exception as e:
            logger.debug(f"Error checking sidebar state: {e}")
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
                # Look for open sidebar button - multiple possible selectors
                open_selectors = [
                    '[aria-label="Open sidebar"]',
                    'button[aria-label*="sidebar"]',
                    'button[aria-controls="stage-slideover-sidebar"]:has([aria-expanded="false"])',
                    'header button:first-child',  # Often the first button in header
                ]
                
                for selector in open_selectors:
                    open_button = self.page.locator(selector).first
                    if await open_button.count() > 0 and await open_button.is_visible():
                        await open_button.click()
                        await asyncio.sleep(get_delay("sidebar_animation"))  # Wait for animation
                        
                        # Force a reflow to ensure icons render properly
                        await self.page.evaluate("""
                            () => {
                                // Force browser to recalculate styles
                                document.body.style.display = 'none';
                                document.body.offsetHeight; // Trigger reflow
                                document.body.style.display = '';
                                
                                // Ensure sidebar icons are visible
                                const sidebarIcons = document.querySelectorAll('nav svg, nav button svg, aside svg');
                                sidebarIcons.forEach(icon => {
                                    if (icon.style.display === 'none' || icon.style.visibility === 'hidden') {
                                        icon.style.display = '';
                                        icon.style.visibility = 'visible';
                                    }
                                });
                            }
                        """)
                        
                        # Verify state changed
                        new_state = await self.is_sidebar_open()
                        if new_state:
                            logger.info("Opened sidebar")
                            return True
                        else:
                            logger.debug(f"Sidebar did not open with selector: {selector}")
            else:
                # Look for close sidebar button - multiple possible selectors
                close_selectors = [
                    '[data-testid="close-sidebar-button"]',
                    '[aria-label="Close sidebar"]',
                    'button[aria-label*="Close"]',
                    'nav button[aria-label*="sidebar"]',  # Button inside the nav
                ]
                
                for selector in close_selectors:
                    close_button = self.page.locator(selector).first
                    if await close_button.count() > 0 and await close_button.is_visible():
                        try:
                            # Try normal click first
                            await close_button.click(timeout=5000)
                        except Exception as e:
                            # If intercepted, use JavaScript click
                            logger.debug(f"Normal click failed, using JavaScript: {e}")
                            await self.page.evaluate("(el) => el.click()", await close_button.element_handle())
                        
                        await asyncio.sleep(get_delay("sidebar_animation"))  # Wait for animation
                        
                        # Force a reflow to fix any rendering issues
                        await self.page.evaluate("""
                            () => {
                                // Force browser to recalculate styles
                                document.body.style.display = 'none';
                                document.body.offsetHeight; // Trigger reflow
                                document.body.style.display = '';
                                
                                // Also check for sidebar icons and ensure they're visible
                                const sidebarIcons = document.querySelectorAll('nav svg, nav button svg');
                                sidebarIcons.forEach(icon => {
                                    if (icon.style.display === 'none' || icon.style.visibility === 'hidden') {
                                        icon.style.display = '';
                                        icon.style.visibility = 'visible';
                                    }
                                });
                            }
                        """)
                        
                        # Verify state changed
                        new_state = await self.is_sidebar_open()
                        if not new_state:
                            logger.info("Closed sidebar")
                            return True
                        else:
                            logger.debug(f"Sidebar did not close with selector: {selector}")
            
            logger.warning(f"Could not {'open' if open else 'close'} sidebar")
            return False
            
        except Exception as e:
            logger.error(f"Failed to toggle sidebar: {e}")
            return False

    async def send_and_get_response(self, message: str, timeout: int = 120) -> str | None:
        """Send message and wait for complete response
        
        Automatically enables web search for research-related queries.
        
        Args:
            message: The message to send
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            The response text or None if failed
        """
        # Check if message needs web search
        research_keywords = [
            "research", "latest", "current", "recent", "2025", "2024", "2026", 
            "update", "new", "find", "search", "discover", "investigate",
            "what's new", "recent changes", "current state", "up to date"
        ]
        message_lower = message.lower()
        enable_web_search = any(kw in message_lower for kw in research_keywords)
        
        if enable_web_search:
            logger.info("Auto-enabling web search due to research keywords")
        
        await self.send_message(message, enable_web_search=enable_web_search)
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

    
    async def enable_think_longer(self) -> bool:
        """Enable Think Longer mode by selecting the gpt-5-thinking model
        
        Based on testing, Think Longer is now automatic with the gpt-5-thinking model
        rather than a separate menu option.
        
        Returns:
            True if Think Longer was enabled (model selected), False otherwise
        """
        if not self.page:
            await self.launch()

        try:
            # Think Longer is now automatic with gpt-5-thinking model
            logger.info("Think Longer is now automatic with gpt-5-thinking model")
            
            # Navigate to gpt-5-thinking model
            current_url = self.page.url
            if "?model=" in current_url:
                # Replace existing model parameter
                new_url = current_url.split("?model=")[0] + "?model=gpt-5-thinking"
            else:
                # Add model parameter
                separator = "&" if "?" in current_url else "?"
                new_url = current_url + separator + "model=gpt-5-thinking"
            
            await self.page.goto(new_url)
            await asyncio.sleep(get_delay("page_load"))
            
            # Verify we're on the thinking model
            model_display = self.page.locator('[data-testid="model-switcher-dropdown-button"]').first
            if await model_display.count() > 0:
                model_text = await model_display.inner_text()
                if "thinking" in model_text.lower() or "5 thinking" in model_text.lower():
                    logger.info(f"Successfully switched to Think Longer mode via {model_text}")
                    return True
            
            # Fallback: Check if URL changed successfully
            if "gpt-5-thinking" in self.page.url:
                logger.info("Think Longer mode enabled via gpt-5-thinking model")
                return True
            
            logger.warning("Could not enable Think Longer mode - model switch may have failed")
            return False
            
        except Exception as e:
            logger.error(f"Failed to enable think longer: {e}")
            return False

    async def enable_deep_research(self) -> bool:
        """Enable Deep Research mode via attachment menu
        
        Deep Research is available as a menu item in the attachment/tools menu.
        
        Note: Deep Research has a monthly quota (250/month)
        
        Returns:
            True if Deep Research was enabled, False otherwise
        """
        if not self.page:
            await self.launch()

        try:
            # Click the attachment/paperclip button
            attachment_selectors = [
                '.composer-btn:not([aria-label*="Dictate"])',  # First composer button (not voice)
                '.composer-btn:not([aria-label*="voice"])',     # Exclude voice button
                'button[aria-label="Attach files"]',            # Legacy selector
                'button:has(svg.icon-paperclip)',               # Legacy selector
            ]
            
            attachment_button = None
            for selector in attachment_selectors:
                button = self.page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    attachment_button = button
                    break
            
            if not attachment_button:
                logger.warning("Attachment button not found")
                return False
                
            await attachment_button.click()
            await asyncio.sleep(get_delay("menu_open"))
            
            # Look for "Deep research" option directly in the menu
            # It's visible in the main menu, not in "More"
            research_selectors = [
                'text="Deep research"',  # Exact text match
                'div:text-is("Deep research")',
                'button:has-text("Deep research")',
                '*:has-text("Deep research")',  # Any element with this text
            ]
            
            for selector in research_selectors:
                option = self.page.locator(selector).first
                if await option.count() > 0 and await option.is_visible():
                    await option.click()
                    logger.info("Clicked Deep Research option")
                    
                    # Wait for Deep Research UI to appear
                    try:
                        # Wait for research-specific UI elements
                        await self.page.wait_for_selector(
                            'text=/researching|sources|web.*search/i',
                            state="visible",
                            timeout=5000
                        )
                    except Exception:
                        # Even if we don't see specific UI, the click likely worked
                        pass
                    
                    logger.info("Enabled Deep Research mode")
                    return True
            
            logger.warning("Deep research option not found in menu")
            # Close menu if still open
            await self.page.keyboard.press("Escape")
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
            # Open Tools menu - try multiple selectors
            tools_button_selectors = [
                'button[aria-label="Choose tool"]',
                '#system-hint-button',
                'button.composer-btn',
                'button[aria-label*="tool"]',
                'button[aria-label*="Tools"]',
                'button[title*="tool"]',
            ]
            
            tools_button = None
            for selector in tools_button_selectors:
                button = self.page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    tools_button = button
                    break
                
            if tools_button and await tools_button.count() > 0 and await tools_button.is_visible():
                await tools_button.click(force=True)
                await asyncio.sleep(get_delay("menu_open"))  # Wait for menu
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
                        await asyncio.sleep(get_delay("ui_update"))

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
                        await asyncio.sleep(get_delay("ui_update"))

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
            logger.debug(f"Found {len(articles)} articles in conversation")
            
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
            
            logger.debug("Found assistant message to regenerate")
            
            # Ensure the response is complete before looking for regenerate button
            if await self._is_responding():
                logger.info("Waiting for response to complete before regenerating...")
                # Wait for response to finish (up to 30 seconds)
                for _ in range(30):
                    if not await self._is_responding():
                        break
                    await asyncio.sleep(1)
                else:
                    logger.warning("Response still generating after 30 seconds")
                    return False
            
            # The regenerate functionality is in the three dots menu button
            # This button has three circle SVG elements
            clicked = False
            menu_button = None
            
            # Take initial screenshot
            await self.page.screenshot(path="regenerate_before_click.png")
            logger.debug("Screenshot saved: regenerate_before_click.png")
            
            # Strategy 1: Find button with three circle elements (three dots menu)
            logger.debug("Looking for three dots menu button...")
            
            # Get all buttons in the last article
            all_buttons = await last_article.locator('button').all()
            logger.debug(f"Found {len(all_buttons)} buttons in last article")
            
            # Look for button with three circle SVG elements
            # The three dots menu is typically the last button in the action row
            for i, button in reversed(list(enumerate(all_buttons))):
                if await button.is_visible():
                    # Count circle elements in this button
                    circles = await button.locator('svg circle').count()
                    aria_label = await button.get_attribute('aria-label') or ""
                    
                    logger.debug(f"  Button {i}: circles={circles}, aria-label='{aria_label}'")
                    
                    # The three dots menu has 3 circle elements and is NOT a copy/like/dislike button
                    if circles == 3 and "Copy" not in aria_label and "Good" not in aria_label:
                        logger.info(f"Found three dots menu button (button {i})")
                        menu_button = button
                        break
                    elif "ChatGPT Actions" in aria_label or "More" in aria_label:
                        logger.info(f"Found menu button by aria-label (button {i})")
                        menu_button = button
                        break
            
            # Strategy 2: Try specific selectors for the three dots button
            if not menu_button:
                logger.debug("Trying specific selectors for three dots button...")
                three_dots_selectors = [
                    'button[aria-label="ChatGPT Actions"]',
                    'button[aria-label="More actions"]',
                    'button[data-testid*="more"]',
                    'button[data-testid*="actions"]',
                    # Look for last button with SVG that's not copy/like/dislike
                    'button:has(svg):not([aria-label*="Copy"]):not([aria-label*="Good"]):not([aria-label*="Bad"]):last-child',
                ]
                
                for selector in three_dots_selectors:
                    button = last_article.locator(selector).first
                    if await button.count() > 0 and await button.is_visible():
                        logger.info(f"Found three dots button with selector: {selector}")
                        menu_button = button
                        break
            
            # Click the three dots menu button
            if menu_button:
                try:
                    # Scroll into view if needed
                    await menu_button.scroll_into_view_if_needed()
                    await asyncio.sleep(get_delay("scroll_delay"))
                    
                    # Try hovering but don't fail if intercepted
                    try:
                        await menu_button.hover(timeout=2000)
                        await asyncio.sleep(get_delay("hover_delay"))
                        # Take screenshot while hovering
                        await self.page.screenshot(path="regenerate_hovering.png")
                        logger.debug("Screenshot saved: regenerate_hovering.png")
                    except Exception as e:
                        logger.debug(f"Hover failed (element intercepted), continuing: {e}")
                    
                    # Try different click methods
                    try:
                        # Method 1: Force click to bypass intercepts
                        await menu_button.click(force=True)
                        logger.info("Clicked three dots menu button with force=True")
                    except Exception as e:
                        logger.debug(f"Force click failed: {e}, trying JavaScript click")
                        # Method 2: JavaScript click
                        await self.page.evaluate("(el) => el.click()", await menu_button.element_handle())
                        logger.info("Clicked three dots menu button with JavaScript")
                    
                    # Wait for menu to open
                    await asyncio.sleep(get_delay("menu_open"))
                    
                    # Take screenshot after clicking
                    await self.page.screenshot(path="regenerate_after_click.png")
                    logger.debug("Screenshot saved: regenerate_after_click.png")
                    
                    # Check if menu opened
                    menu_items = await self.page.locator('[role="menuitem"]').all()
                    if len(menu_items) > 0:
                        clicked = True
                        logger.info(f"Menu opened with {len(menu_items)} items")
                        
                        # Log menu items for debugging
                        for item in menu_items:
                            item_text = await item.text_content()
                            logger.debug(f"  Menu item: {item_text}")
                    else:
                        logger.warning("Menu did not open after clicking")
                        
                except Exception as e:
                    logger.error(f"Failed to click three dots menu: {e}")
                    await self.page.screenshot(path="regenerate_error.png")
            else:
                logger.error("Could not find three dots menu button")
                await self.page.screenshot(path="regenerate_button_debug.png")
                return False
            
            # If menu opened, look for "Try again" option
            if clicked:
                try_again_selectors = [
                    'text="Try again"',  # Exact text match
                    '[role="menuitem"]:has-text("Try again")',
                    'button:has-text("Try again")',
                    'div:has-text("Try again")',
                ]
                
                for selector in try_again_selectors:
                    try_again = self.page.locator(selector).first
                    if await try_again.count() > 0 and await try_again.is_visible():
                        await try_again.click()
                        logger.info("Clicked 'Try again' to regenerate response")
                        
                        # Wait for regeneration to start
                        await asyncio.sleep(get_delay("ui_update"))
                        
                        # Close any open dropdowns
                        await self.page.keyboard.press("Escape")
                        
                        return True
                
                # If not found, close the dropdown
                await self.page.keyboard.press("Escape")
                logger.warning("'Try again' option not found in menu")
                await self.page.screenshot(path="regenerate_menu_debug.png")
            
            return False

        except Exception as e:
            logger.error(f"Failed to regenerate response: {e}")
            try:
                await self.page.screenshot(path="regenerate_error_debug.png")
                logger.debug("Error screenshot saved")
            except:
                pass
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
                await asyncio.sleep(get_delay("menu_open"))  # Wait for menu
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
                                await asyncio.sleep(get_delay("ui_update"))
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
            await asyncio.sleep(get_delay("ui_update"))
            
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

                elif operation_name == "enable_think_longer":
                    op_result["result"] = await self.enable_think_longer()
                    op_result["success"] = op_result["result"]

                elif operation_name == "enable_deep_research":
                    op_result["result"] = await self.enable_deep_research()
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
