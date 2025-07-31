"""
Tests for comprehensive error handling and recovery system
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, Mock
from playwright.async_api import TimeoutError as PlaywrightTimeout

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController
from chatgpt_automation_mcp.error_recovery import (
    ErrorType,
    RecoveryAction,
    ErrorRecoveryManager,
    ChatGPTErrorRecovery,
    with_error_recovery
)


class TestErrorRecoveryManager:
    """Test the error recovery manager"""
    
    def test_error_type_classification(self):
        """Test error classification logic"""
        manager = ErrorRecoveryManager()
        
        # Network errors
        network_error = Exception("Network connection failed")
        assert manager.classify_error(network_error) == ErrorType.NETWORK_ERROR
        
        # Timeout errors
        timeout_error = PlaywrightTimeout("Timeout waiting for selector")
        assert manager.classify_error(timeout_error) == ErrorType.TIMEOUT_ERROR
        
        # Rate limit errors
        rate_error = Exception("Rate limit exceeded")
        assert manager.classify_error(rate_error) == ErrorType.RATE_LIMIT
        
        # Browser crash errors
        browser_error = Exception("Browser disconnected unexpectedly")
        assert manager.classify_error(browser_error) == ErrorType.BROWSER_CRASH
        
        # Element not found errors
        element_error = Exception("Element not found by selector")
        assert manager.classify_error(element_error) == ErrorType.ELEMENT_NOT_FOUND
        
        # Unknown errors
        unknown_error = Exception("Something completely different")
        assert manager.classify_error(unknown_error) == ErrorType.UNKNOWN_ERROR
    
    @pytest.mark.asyncio
    async def test_recovery_action_registration(self):
        """Test registering recovery actions"""
        manager = ErrorRecoveryManager()
        
        # Mock recovery action
        recovery_func = AsyncMock()
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=2,
            delay=1.0,
            description="Test recovery"
        )
        
        manager.register_recovery_action(action)
        assert ErrorType.NETWORK_ERROR in manager.recovery_actions
        assert manager.recovery_actions[ErrorType.NETWORK_ERROR] == action
    
    @pytest.mark.asyncio
    async def test_successful_error_recovery(self):
        """Test successful error recovery flow"""
        manager = ErrorRecoveryManager()
        
        # Mock recovery action
        recovery_func = AsyncMock()
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=2,
            delay=0.1,  # Short delay for testing
            description="Test recovery"
        )
        manager.register_recovery_action(action)
        
        # Test successful recovery
        error = Exception("Network connection failed")
        result = await manager.handle_error(error, "test_context")
        
        assert result is True
        recovery_func.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_failed_error_recovery(self):
        """Test failed error recovery flow"""
        manager = ErrorRecoveryManager()
        
        # Mock recovery action that fails
        recovery_func = AsyncMock(side_effect=Exception("Recovery failed"))
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=1,
            delay=0.1,
            description="Test recovery"
        )
        manager.register_recovery_action(action)
        
        # Test failed recovery
        error = Exception("Network connection failed")
        result = await manager.handle_error(error, "test_context")
        
        assert result is False
        recovery_func.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test max retries exceeded scenario"""
        manager = ErrorRecoveryManager()
        
        recovery_func = AsyncMock(side_effect=Exception("Recovery failed"))
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=2,
            delay=0.1,
            description="Test recovery"
        )
        manager.register_recovery_action(action)
        
        error = Exception("Network connection failed")
        context = "test_context"
        
        # First attempt should fail and increment retry count
        result1 = await manager.handle_error(error, context)
        assert result1 is False
        assert manager.retry_counts[f"{ErrorType.NETWORK_ERROR.value}:{context}"] == 1
        
        # Second attempt should fail and increment retry count
        result2 = await manager.handle_error(error, context)
        assert result2 is False
        assert manager.retry_counts[f"{ErrorType.NETWORK_ERROR.value}:{context}"] == 2
        
        # Third attempt should exceed max retries and reset count
        result3 = await manager.handle_error(error, context)
        assert result3 is False
        assert manager.retry_counts[f"{ErrorType.NETWORK_ERROR.value}:{context}"] == 0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff delay calculation"""
        manager = ErrorRecoveryManager()
        
        start_times = []
        async def capture_time():
            start_times.append(asyncio.get_event_loop().time())
        
        recovery_func = AsyncMock(side_effect=[Exception("Fail 1"), Exception("Fail 2"), capture_time])
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=3,
            delay=0.1,
            exponential_backoff=True,
            description="Test backoff"
        )
        manager.register_recovery_action(action)
        
        error = Exception("Network connection failed")
        
        # First attempt (delay = 0.1 * 2^0 = 0.1)
        await manager.handle_error(error, "test")
        
        # Second attempt (delay = 0.1 * 2^1 = 0.2)  
        await manager.handle_error(error, "test")
        
        # Third attempt (delay = 0.1 * 2^2 = 0.4)
        await manager.handle_error(error, "test")
        
        # Verify exponential backoff timing (allowing for some variance)
        if len(start_times) >= 2:
            delay1 = start_times[1] - start_times[0]
            assert delay1 >= 0.15  # Should be at least 0.2 seconds
    
    @pytest.mark.asyncio
    async def test_no_recovery_action_registered(self):
        """Test behavior when no recovery action is registered for error type"""
        manager = ErrorRecoveryManager()
        
        # No recovery action registered for UNKNOWN_ERROR
        error = Exception("Some unknown error")
        result = await manager.handle_error(error, "test_context")
        
        assert result is False


class TestChatGPTErrorRecovery:
    """Test ChatGPT-specific error recovery strategies"""
    
    @pytest.mark.asyncio
    async def test_chatgpt_error_recovery_initialization(self):
        """Test ChatGPT error recovery setup"""
        controller = ChatGPTBrowserController()
        recovery = ChatGPTErrorRecovery(controller)
        
        # Verify recovery actions are registered
        assert ErrorType.BROWSER_CRASH in recovery.recovery_manager.recovery_actions
        assert ErrorType.SESSION_EXPIRED in recovery.recovery_manager.recovery_actions
        assert ErrorType.RATE_LIMIT in recovery.recovery_manager.recovery_actions
        assert ErrorType.NETWORK_ERROR in recovery.recovery_manager.recovery_actions
        assert ErrorType.ELEMENT_NOT_FOUND in recovery.recovery_manager.recovery_actions
        assert ErrorType.TIMEOUT_ERROR in recovery.recovery_manager.recovery_actions
    
    @pytest.mark.asyncio
    async def test_browser_crash_recovery(self):
        """Test browser crash recovery strategy"""
        controller = ChatGPTBrowserController()
        controller.close = AsyncMock()
        controller.launch = AsyncMock()
        
        recovery = ChatGPTErrorRecovery(controller)
        
        # Simulate browser crash recovery
        await recovery._recover_browser_crash()
        
        controller.close.assert_called_once()
        controller.launch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_expired_recovery(self):
        """Test session expiration recovery strategy"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller._needs_login = AsyncMock(return_value=True)
        controller._handle_login = AsyncMock()
        
        recovery = ChatGPTErrorRecovery(controller)
        
        # Simulate session expired recovery
        await recovery._recover_session_expired()
        
        controller.page.goto.assert_called_once_with("https://chatgpt.com", wait_until="domcontentloaded")
        controller._needs_login.assert_called_once()
        controller._handle_login.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_network_error_recovery(self):
        """Test network error recovery strategy"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        
        recovery = ChatGPTErrorRecovery(controller)
        
        # Simulate network error recovery
        await recovery._recover_network_error()
        
        # Should try to reload the page
        controller.page.reload.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_element_not_found_recovery(self):
        """Test element not found recovery strategy"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        
        recovery = ChatGPTErrorRecovery(controller)
        
        # Simulate element not found recovery
        await recovery._recover_element_not_found()
        
        # Should reload page and wait for elements
        controller.page.reload.assert_called_once()


class TestBrowserControllerErrorRecovery:
    """Test error recovery integration in browser controller"""
    
    @pytest.mark.asyncio
    async def test_get_current_model_with_recovery(self):
        """Test get_current_model with error recovery"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller.error_recovery = AsyncMock()
        controller.error_recovery.handle_error = AsyncMock(return_value=True)
        
        # Mock implementation method to fail first time, succeed second time
        controller._get_current_model_impl = AsyncMock(
            side_effect=[Exception("Test error"), "gpt-4"]
        )
        
        # Should recover and succeed
        result = await controller.get_current_model()
        assert result == "gpt-4"
        
        # Error recovery should have been called
        controller.error_recovery.handle_error.assert_called_once()
        
        # Implementation should have been called twice (fail, then succeed)
        assert controller._get_current_model_impl.call_count == 2
    
    @pytest.mark.asyncio
    async def test_select_model_with_recovery(self):
        """Test select_model with error recovery"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller.error_recovery = AsyncMock()
        controller.error_recovery.handle_error = AsyncMock(return_value=True)
        
        # Mock implementation method to fail first time, succeed second time
        controller._select_model_impl = AsyncMock(
            side_effect=[Exception("Test error"), True]
        )
        
        # Should recover and succeed
        result = await controller.select_model("gpt-4")
        assert result is True
        
        # Error recovery should have been called
        controller.error_recovery.handle_error.assert_called_once()
        
        # Implementation should have been called twice (fail, then succeed)
        assert controller._select_model_impl.call_count == 2
    
    @pytest.mark.asyncio
    async def test_new_chat_with_recovery(self):
        """Test new_chat with error recovery"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller.error_recovery = AsyncMock()
        controller.error_recovery.handle_error = AsyncMock(return_value=True)
        
        # Mock implementation method to fail first time, succeed second time
        controller._new_chat_impl = AsyncMock(
            side_effect=[Exception("Test error"), "New chat started"]
        )
        
        # Should recover and succeed
        result = await controller.new_chat()
        assert result == "New chat started"
        
        # Error recovery should have been called
        controller.error_recovery.handle_error.assert_called_once()
        
        # Implementation should have been called twice (fail, then succeed)
        assert controller._new_chat_impl.call_count == 2
    
    @pytest.mark.asyncio
    async def test_wait_for_response_with_recovery(self):
        """Test wait_for_response with error recovery"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller.error_recovery = AsyncMock()
        controller.error_recovery.handle_error = AsyncMock(return_value=True)
        
        # Mock implementation method to fail first time, succeed second time
        controller._wait_for_response_impl = AsyncMock(
            side_effect=[Exception("Test error"), True]
        )
        
        # Should recover and succeed
        result = await controller.wait_for_response(30)
        assert result is True
        
        # Error recovery should have been called
        controller.error_recovery.handle_error.assert_called_once()
        
        # Implementation should have been called twice (fail, then succeed)
        assert controller._wait_for_response_impl.call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_recovery_failure(self):
        """Test behavior when error recovery fails"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller.error_recovery = AsyncMock()
        controller.error_recovery.handle_error = AsyncMock(return_value=False)  # Recovery fails
        
        # Mock implementation method to always fail
        controller._get_current_model_impl = AsyncMock(side_effect=Exception("Test error"))
        
        # Should return None when recovery fails
        result = await controller.get_current_model()
        assert result is None
        
        # Error recovery should have been called
        controller.error_recovery.handle_error.assert_called_once()
        
        # Implementation should have been called only once (no retry after failed recovery)
        assert controller._get_current_model_impl.call_count == 1
    
    @pytest.mark.asyncio
    async def test_no_error_recovery_available(self):
        """Test behavior when no error recovery is available"""
        controller = ChatGPTBrowserController()
        controller.page = AsyncMock()
        controller.error_recovery = None  # No error recovery
        
        # Mock implementation method to fail
        controller._get_current_model_impl = AsyncMock(side_effect=Exception("Test error"))
        
        # Should return None when no recovery available
        result = await controller.get_current_model()
        assert result is None
        
        # Implementation should have been called only once
        assert controller._get_current_model_impl.call_count == 1


class TestErrorRecoveryDecorator:
    """Test the error recovery decorator"""
    
    @pytest.mark.asyncio
    async def test_with_error_recovery_decorator_success(self):
        """Test decorator with successful function execution"""
        manager = ErrorRecoveryManager()
        
        @with_error_recovery(manager, "test_context")
        async def test_function():
            return "success"
        
        result = await test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_with_error_recovery_decorator_with_recovery(self):
        """Test decorator with error recovery"""
        manager = ErrorRecoveryManager()
        
        # Setup recovery action
        recovery_func = AsyncMock()
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=1,
            delay=0.1,
            description="Test recovery"
        )
        manager.register_recovery_action(action)
        
        call_count = 0
        
        @with_error_recovery(manager, "test_context")
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network connection failed")
            return "success after recovery"
        
        result = await test_function()
        assert result == "success after recovery"
        assert call_count == 2  # Failed once, then succeeded
        recovery_func.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_with_error_recovery_decorator_max_attempts(self):
        """Test decorator with max attempts exceeded"""
        manager = ErrorRecoveryManager()
        
        # Setup recovery action that always fails
        recovery_func = AsyncMock(side_effect=Exception("Recovery failed"))
        action = RecoveryAction(
            error_type=ErrorType.NETWORK_ERROR,
            action=recovery_func,
            max_retries=1,
            delay=0.1,
            description="Test recovery"
        )
        manager.register_recovery_action(action)
        
        @with_error_recovery(manager, "test_context")
        async def test_function():
            raise Exception("Network connection failed")
        
        with pytest.raises(Exception, match="Network connection failed"):
            await test_function()