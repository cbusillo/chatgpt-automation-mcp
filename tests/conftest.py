"""
Pytest configuration and fixtures for ChatGPT Automation MCP tests.
Provides browser setup, screenshot utilities, and test environment detection.
"""

import asyncio
import pytest
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator
import sys

# CRITICAL: Set test environment BEFORE any imports from src
# This ensures Config class sees the correct environment variables
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("USE_CDP", "true")  # Use CDP like production to work with ChatGPT
os.environ.setdefault("HEADLESS", "false")  # Use visible browser
os.environ.setdefault("CDP_URL", "http://127.0.0.1:9222")  # Standard CDP port

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


# Test environment configuration
SKIP_BROWSER_TESTS = os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true"
SKIP_INTEGRATION_TESTS = os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true"
HEADLESS_MODE = os.getenv("HEADLESS", "true").lower() == "true"
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "120"))  # Default 2 minutes

# Screenshot directory setup
SCREENSHOTS_DIR = Path(__file__).parent / "test_screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


class BrowserTestFixture:
    """Enhanced browser fixture with screenshot capabilities and proper cleanup"""
    
    def __init__(self, controller: ChatGPTBrowserController):
        self.controller = controller
        self.test_name = "unknown"
        self.screenshot_counter = 0
    
    async def screenshot(self, name: str = None) -> Path:
        """Take a screenshot with automatic naming and storage"""
        if name is None:
            name = f"step_{self.screenshot_counter:02d}"
            self.screenshot_counter += 1
        
        filename = f"{self.test_name}_{name}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        if self.controller.page:
            await self.controller.page.screenshot(path=str(filepath))
            return filepath
        
        return None
    
    async def verify_element(self, selector: str, expected_count: int = 1, name: str = None) -> bool:
        """Verify element presence with screenshot evidence"""
        if not self.controller.page:
            return False
        
        count = await self.controller.page.locator(selector).count()
        success = count == expected_count
        
        # Take screenshot for verification
        clean_selector = selector.replace(' ', '_').replace('"', '').replace('[', '').replace(']', '')[:20]
        screenshot_name = name or f"verify_{clean_selector}"
        await self.screenshot(f"{screenshot_name}_{'pass' if success else 'fail'}")
        
        return success
    
    async def wait_for_stable_ui(self, timeout: int = 5):
        """Wait for UI to stabilize (useful after navigation or clicks)"""
        if self.controller.page:
            try:
                await self.controller.page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            except:
                pass  # Continue if networkidle times out
            
            # Small additional wait for animations
            await asyncio.sleep(0.5)


@pytest.fixture
async def browser() -> AsyncGenerator[BrowserTestFixture, None]:
    """
    Browser fixture with enhanced capabilities:
    - Automatic cleanup
    - Screenshot support
    - Environment detection
    - Proper error handling
    """
    if SKIP_BROWSER_TESTS:
        pytest.skip("Browser tests disabled via SKIP_BROWSER_TESTS=true")
    
    controller = None
    fixture = None
    
    try:
        controller = ChatGPTBrowserController()
        fixture = BrowserTestFixture(controller)
        
        # Launch browser with appropriate settings
        await controller.launch()
        
        # Verify browser is working
        if not controller.page:
            raise RuntimeError("Browser failed to launch properly")
        
        # Take initial screenshot
        fixture.test_name = "startup"
        await fixture.screenshot("browser_launched")
        
        yield fixture
        
    except Exception as e:
        # Capture failure screenshot if possible
        if fixture and hasattr(fixture, 'controller') and fixture.controller.page:
            try:
                await fixture.screenshot("fixture_error")
            except Exception:
                pass  # Don't fail cleanup on screenshot error
        raise e
    
    finally:
        # Guaranteed cleanup
        if controller:
            try:
                if controller.page:
                    await fixture.screenshot("cleanup_before") if fixture else None
                    await controller.page.close()
            except Exception as cleanup_error:
                # Log cleanup error but don't fail the test
                print(f"Warning: Browser cleanup failed: {cleanup_error}")
                
            # Force cleanup if normal cleanup failed
            try:
                await controller.close()
            except Exception:
                pass


@pytest.fixture
async def integration_browser(browser) -> AsyncGenerator[BrowserTestFixture, None]:
    """Integration test browser fixture (separate from unit tests)"""
    if SKIP_INTEGRATION_TESTS:
        pytest.skip("Integration tests disabled via SKIP_INTEGRATION_TESTS=true")
    
    # Use same browser fixture but with different skip condition
    yield browser


@pytest.fixture(autouse=True)
def setup_test_name(request):
    """Automatically set test name for screenshots"""
    test_name = request.node.name.replace("::", "_").replace("[", "_").replace("]", "_")
    # Store test name for browser fixture
    if hasattr(request, 'param'):
        test_name += f"_{request.param}"
    
    # This will be picked up by browser fixture
    os.environ['CURRENT_TEST_NAME'] = test_name


@pytest.fixture(scope="session", autouse=True)
def cleanup_screenshots():
    """Clean up old screenshots at session start and manage storage"""
    if SCREENSHOTS_DIR.exists():
        # Remove old screenshots older than 24 hours (not 7 days - too much storage)
        import time
        current_time = time.time()
        cleaned_count = 0
        
        for screenshot in SCREENSHOTS_DIR.glob("*.png"):
            try:
                if current_time - screenshot.stat().st_mtime > 24 * 3600:  # 24 hours
                    screenshot.unlink()
                    cleaned_count += 1
            except Exception:
                pass  # Ignore cleanup errors
        
        if cleaned_count > 0:
            print(f"Cleaned up {cleaned_count} old screenshot files")
        
        # Check total screenshot count and clean up excess
        all_screenshots = list(SCREENSHOTS_DIR.glob("*.png"))
        if len(all_screenshots) > 100:  # Keep max 100 screenshots
            # Remove oldest files
            all_screenshots.sort(key=lambda p: p.stat().st_mtime)
            for old_screenshot in all_screenshots[:-50]:  # Keep newest 50
                try:
                    old_screenshot.unlink()
                except Exception:
                    pass
            print(f"Cleaned up excess screenshots (kept 50 most recent)")
    
    yield
    
    # Clean up test session screenshots if in CI environment
    if os.getenv("CI", "false").lower() == "true":
        try:
            for screenshot in SCREENSHOTS_DIR.glob("*.png"):
                screenshot.unlink()
            print("Cleaned up all screenshots (CI mode)")
        except Exception:
            pass


# Custom pytest markers
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line(
        "markers", "browser: mark test as requiring browser automation"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring full setup"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (may take minutes)"
    )
    config.addinivalue_line(
        "markers", "ui_dependent: mark test as dependent on current ChatGPT UI"
    )


# Test collection hook to set test names
def pytest_runtest_setup(item):
    """Set up test environment before each test"""
    test_name = item.name.replace("::", "_").replace("[", "_").replace("]", "_")
    os.environ['CURRENT_TEST_NAME'] = test_name


# Test isolation utilities
async def reset_browser_state(controller):
    """Reset browser to clean state between tests"""
    if not controller or not controller.page:
        return
    
    try:
        # Start new conversation to isolate tests
        await controller.new_chat()
        
        # Clear any modals or overlays
        await controller.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        
        # Ensure sidebar is in consistent state
        await controller.toggle_sidebar(open=False)
        
    except Exception as e:
        # If reset fails, we'll need a fresh browser
        print(f"Warning: Cannot reset browser state: {e}")


@pytest.fixture
async def test_isolation(request):
    """Isolate tests that use browser fixtures (only runs when browser tests are active)"""
    # This runs before each test
    yield
    
    # This runs after each test
    if hasattr(request, 'node') and any('browser' in fname for fname in request.fixturenames):
        # Test used browser fixture - ensure clean state for next test
        try:
            # Get the browser fixture from the test
            for fixture_name in request.fixturenames:
                if 'browser' in fixture_name:
                    browser_fixture = request.getfixturevalue(fixture_name)
                    if browser_fixture and hasattr(browser_fixture, 'controller'):
                        await reset_browser_state(browser_fixture.controller)
                    break
        except Exception:
            # If cleanup fails, that's okay - next test will handle it
            pass