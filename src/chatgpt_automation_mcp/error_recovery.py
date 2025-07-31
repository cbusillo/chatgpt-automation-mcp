"""
Comprehensive error handling and recovery system for ChatGPT automation
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can occur during automation"""

    NETWORK_ERROR = "network_error"
    ELEMENT_NOT_FOUND = "element_not_found"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT = "rate_limit"
    SESSION_EXPIRED = "session_expired"
    AUTHENTICATION_ERROR = "authentication_error"
    BROWSER_CRASH = "browser_crash"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class RecoveryAction:
    """Defines a recovery action for a specific error type"""

    error_type: ErrorType
    action: Callable[[], Any]
    max_retries: int = 3
    delay: float = 1.0
    exponential_backoff: bool = True
    description: str = ""


class ErrorRecoveryManager:
    """Manages error detection, classification, and recovery strategies"""

    def __init__(self):
        self.recovery_actions: dict[ErrorType, RecoveryAction] = {}
        self.retry_counts: dict[str, int] = {}

    def register_recovery_action(self, action: RecoveryAction):
        """Register a recovery action for a specific error type"""
        self.recovery_actions[action.error_type] = action
        logger.info(
            f"Registered recovery action for {action.error_type.value}: {action.description}"
        )

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an error into one of the defined error types"""
        error_message = str(error).lower()

        # Network-related errors
        if any(keyword in error_message for keyword in ["network", "connection", "dns", "host"]):
            return ErrorType.NETWORK_ERROR

        # Playwright timeout errors
        if isinstance(error, PlaywrightTimeout) or "timeout" in error_message:
            return ErrorType.TIMEOUT_ERROR

        # Rate limiting
        if any(
            keyword in error_message for keyword in ["rate limit", "too many requests", "quota"]
        ):
            return ErrorType.RATE_LIMIT

        # Authentication errors
        if any(
            keyword in error_message for keyword in ["unauthorized", "forbidden", "login", "auth"]
        ):
            return ErrorType.AUTHENTICATION_ERROR

        # Session expiration
        if any(keyword in error_message for keyword in ["session", "expired", "invalid session"]):
            return ErrorType.SESSION_EXPIRED

        # Browser crash
        if any(
            keyword in error_message for keyword in ["browser", "crash", "closed", "disconnected"]
        ):
            return ErrorType.BROWSER_CRASH

        # Element not found (common in UI automation)
        if any(
            keyword in error_message for keyword in ["element not found", "selector", "locator"]
        ):
            return ErrorType.ELEMENT_NOT_FOUND

        return ErrorType.UNKNOWN_ERROR

    async def handle_error(self, error: Exception, context: str = "") -> bool:
        """Handle an error using registered recovery actions

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            True if recovery was successful, False otherwise
        """
        error_type = self.classify_error(error)
        retry_key = f"{error_type.value}:{context}"

        logger.warning(f"Error detected in {context}: {error_type.value} - {error}")

        # Check if we have a recovery action for this error type
        if error_type not in self.recovery_actions:
            logger.error(f"No recovery action registered for {error_type.value}")
            return False

        recovery_action = self.recovery_actions[error_type]
        current_retries = self.retry_counts.get(retry_key, 0)

        # Check if we've exceeded max retries
        if current_retries >= recovery_action.max_retries:
            logger.error(
                f"Max retries ({recovery_action.max_retries}) exceeded for {error_type.value}"
            )
            self.retry_counts[retry_key] = 0  # Reset for future attempts
            return False

        # Calculate delay with exponential backoff
        delay = recovery_action.delay
        if recovery_action.exponential_backoff:
            delay *= 2**current_retries

        logger.info(
            f"Attempting recovery for {error_type.value} (attempt {current_retries + 1}/{recovery_action.max_retries})"
        )

        # Wait before attempting recovery
        if delay > 0:
            logger.info(f"Waiting {delay:.1f}s before recovery attempt...")
            await asyncio.sleep(delay)

        try:
            # Execute recovery action
            await recovery_action.action()
            logger.info(f"Recovery successful for {error_type.value}")
            self.retry_counts[retry_key] = 0  # Reset retry count on success
            return True

        except Exception as recovery_error:
            self.retry_counts[retry_key] = current_retries + 1
            logger.error(f"Recovery attempt failed: {recovery_error}")
            return False

    def reset_retry_counts(self, error_type: ErrorType | None = None):
        """Reset retry counts for all or specific error types"""
        if error_type:
            keys_to_reset = [
                key for key in self.retry_counts.keys() if key.startswith(error_type.value)
            ]
            for key in keys_to_reset:
                self.retry_counts[key] = 0
            logger.info(f"Reset retry counts for {error_type.value}")
        else:
            self.retry_counts.clear()
            logger.info("Reset all retry counts")


def with_error_recovery(recovery_manager: ErrorRecoveryManager, context: str = ""):
    """Decorator for methods that should use error recovery"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            max_attempts = 3
            last_error = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    # Only attempt recovery on first few attempts
                    if attempt < max_attempts - 1:
                        recovery_successful = await recovery_manager.handle_error(
                            e, context or func.__name__
                        )
                        if recovery_successful:
                            continue  # Retry the original function

                    # If we reach here, either recovery failed or this is the last attempt
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts"
                        )
                        raise last_error

            raise last_error

        return wrapper

    return decorator


class ChatGPTErrorRecovery:
    """Specific error recovery strategies for ChatGPT automation"""

    def __init__(self, browser_controller):
        self.controller = browser_controller
        self.recovery_manager = ErrorRecoveryManager()
        self._setup_recovery_actions()

    def _setup_recovery_actions(self):
        """Set up default recovery actions for ChatGPT automation"""

        # Browser crash recovery
        self.recovery_manager.register_recovery_action(
            RecoveryAction(
                error_type=ErrorType.BROWSER_CRASH,
                action=self._recover_browser_crash,
                max_retries=2,
                delay=5.0,
                description="Restart browser and restore session",
            )
        )

        # Session expired recovery
        self.recovery_manager.register_recovery_action(
            RecoveryAction(
                error_type=ErrorType.SESSION_EXPIRED,
                action=self._recover_session_expired,
                max_retries=2,
                delay=2.0,
                description="Re-authenticate and restore session",
            )
        )

        # Rate limit recovery
        self.recovery_manager.register_recovery_action(
            RecoveryAction(
                error_type=ErrorType.RATE_LIMIT,
                action=self._recover_rate_limit,
                max_retries=3,
                delay=30.0,
                exponential_backoff=True,
                description="Wait for rate limit to reset",
            )
        )

        # Network error recovery
        self.recovery_manager.register_recovery_action(
            RecoveryAction(
                error_type=ErrorType.NETWORK_ERROR,
                action=self._recover_network_error,
                max_retries=3,
                delay=5.0,
                description="Wait and retry network connection",
            )
        )

        # Element not found recovery
        self.recovery_manager.register_recovery_action(
            RecoveryAction(
                error_type=ErrorType.ELEMENT_NOT_FOUND,
                action=self._recover_element_not_found,
                max_retries=2,
                delay=3.0,
                description="Refresh page and wait for elements",
            )
        )

        # Timeout error recovery
        self.recovery_manager.register_recovery_action(
            RecoveryAction(
                error_type=ErrorType.TIMEOUT_ERROR,
                action=self._recover_timeout_error,
                max_retries=2,
                delay=2.0,
                description="Wait and retry with extended timeout",
            )
        )

    async def _recover_browser_crash(self):
        """Recover from browser crash by restarting"""
        logger.info("Recovering from browser crash...")
        await self.controller.close()
        await asyncio.sleep(2)
        await self.controller.launch()

    async def _recover_session_expired(self):
        """Recover from session expiration"""
        logger.info("Recovering from session expiration...")
        # Navigate back to ChatGPT and check if login is needed
        if self.controller.page:
            await self.controller.page.goto("https://chatgpt.com", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Check if we need to login again
            needs_login = await self.controller._needs_login()
            if needs_login:
                await self.controller._handle_login()

    async def _recover_rate_limit(self):
        """Recover from rate limiting"""
        logger.info("Recovering from rate limit...")
        # Just wait - the delay is handled by the recovery manager
        pass

    async def _recover_network_error(self):
        """Recover from network errors"""
        logger.info("Recovering from network error...")
        # Wait for network to stabilize
        await asyncio.sleep(2)

        # Try to refresh the page if we have one
        if self.controller.page:
            try:
                await self.controller.page.reload(wait_until="domcontentloaded", timeout=10000)
            except Exception:
                # If reload fails, try navigating to ChatGPT again
                await self.controller.page.goto(
                    "https://chatgpt.com", wait_until="domcontentloaded", timeout=15000
                )

    async def _recover_element_not_found(self):
        """Recover from element not found errors"""
        logger.info("Recovering from element not found...")
        if self.controller.page:
            # Wait a bit for the page to load
            await asyncio.sleep(2)

            # Try refreshing the page
            try:
                await self.controller.page.reload(wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(3)  # Wait for elements to load
            except Exception:
                logger.warning("Page reload failed during element recovery")

    async def _recover_timeout_error(self):
        """Recover from timeout errors"""
        logger.info("Recovering from timeout error...")
        # Wait for any ongoing operations to complete
        await asyncio.sleep(3)

        # Check if page is still responsive
        if self.controller.page:
            try:
                await self.controller.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                logger.warning("Page not responsive during timeout recovery")

    async def handle_error(self, error: Exception, context: str = "") -> bool:
        """Handle an error using the recovery manager"""
        return await self.recovery_manager.handle_error(error, context)

    def with_recovery(self, context: str = ""):
        """Decorator for methods that should use error recovery"""
        return with_error_recovery(self.recovery_manager, context)
