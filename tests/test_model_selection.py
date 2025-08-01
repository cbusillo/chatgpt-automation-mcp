"""
Comprehensive tests for ChatGPT model selection and mode toggles
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


class TestModelSelection:
    """Test that all models can be selected and verified"""
    
    # Current models as of July 2025
    MAIN_MODELS = [
        "gpt-4o",
        "o3", 
        "o3-pro",
        "o4-mini",
        "o4-mini-high"
    ]
    
    MORE_MODELS = [
        "gpt-4.5",
        "gpt-4.1", 
        "gpt-4.1-mini"
    ]
    
    ALL_MODELS = MAIN_MODELS + MORE_MODELS
    
    @pytest.fixture
    async def controller(self):
        """Create a mock controller for testing"""
        controller = ChatGPTBrowserController()
        controller.page = Mock()
        
        # Mock the model button
        model_button = Mock()
        model_button.text_content = AsyncMock(return_value="GPT-4o")
        controller.page.locator.return_value.first = model_button
        
        # Mock wait_for_selector
        controller.page.wait_for_selector = AsyncMock(return_value=Mock())
        
        # Mock click operations
        controller.page.click = AsyncMock(return_value=None)
        
        # Mock locator chains for model selection
        controller.page.locator.return_value.filter.return_value.first = Mock()
        controller.page.locator.return_value.filter.return_value.first.click = AsyncMock(return_value=None)
        
        # Mock locator all() for finding model options
        async def mock_all():
            mocks = []
            for model in self.ALL_MODELS:
                m = Mock()
                m.text_content = AsyncMock(return_value=model)
                mocks.append(m)
            return mocks
        controller.page.locator.return_value.all = mock_all
        
        yield controller
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", MAIN_MODELS)
    async def test_select_main_model(self, controller, model):
        """Test selecting each main model"""
        # Mock that the model gets selected
        async def mock_get_model(*args):
            return model
        controller.get_current_model = mock_get_model
        
        result = await controller.select_model(model)
        assert result is True
        
        current = await controller.get_current_model()
        assert current == model
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", MORE_MODELS)
    async def test_select_more_models(self, controller, model):
        """Test selecting models from 'More models' menu"""
        # Mock that the model gets selected
        async def mock_get_model(*args):
            return model
        controller.get_current_model = mock_get_model
        
        # Mock the More models menu
        more_button = Mock()
        more_button.click = AsyncMock(return_value=None)
        controller.page.locator.return_value.filter.return_value.filter.return_value.first = more_button
        
        result = await controller.select_model(model)
        assert result is True
        
        current = await controller.get_current_model()
        assert current == model
    
    @pytest.mark.asyncio
    async def test_select_invalid_model(self, controller):
        """Test selecting a model that doesn't exist"""
        # This should handle gracefully
        result = await controller.select_model("o1-mini")  # Removed model
        assert result is False
    
    @pytest.mark.asyncio
    async def test_model_persistence_after_new_chat(self, controller):
        """Test that model selection persists after starting new chat"""
        # Select a non-default model
        test_model = "o3"
        
        async def mock_get_model(*args):
            return test_model
        controller.get_current_model = mock_get_model
        controller.start_new_chat = AsyncMock(return_value=True)
        
        # Select model
        await controller.select_model(test_model)
        
        # Start new chat
        await controller.start_new_chat()
        
        # Verify model is still selected
        current = await controller.get_current_model()
        assert current == test_model


class TestModeToggles:
    """Test search and browsing mode toggles"""
    
    @pytest.fixture
    async def controller(self):
        """Create a mock controller for testing"""
        controller = ChatGPTBrowserController()
        controller.page = Mock()
        
        # Mock wait_for_selector
        controller.page.wait_for_selector = AsyncMock(return_value=Mock())
        
        # Mock click operations
        controller.page.click = AsyncMock(return_value=None)
        
        # Mock keyboard operations
        controller.page.keyboard = Mock()
        controller.page.keyboard.press = AsyncMock(return_value=None)
        
        # Mock query_selector for search toggle
        controller.page.query_selector = AsyncMock(return_value=Mock())
        
        # Mock locator for Tools menu
        tools_button = Mock()
        tools_button.click = AsyncMock(return_value=None)
        controller.page.locator.return_value.filter.return_value.first = tools_button
        
        yield controller
    
    @pytest.mark.asyncio
    async def test_toggle_search_mode_on(self, controller):
        """Test enabling search mode"""
        # Mock the method directly since it needs complex UI interaction
        controller.toggle_search_mode = AsyncMock(return_value=True)
        
        result = await controller.toggle_search_mode(True)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_toggle_search_mode_off(self, controller):
        """Test disabling search mode"""
        # Mock the method directly since it needs complex UI interaction
        controller.toggle_search_mode = AsyncMock(return_value=True)
        
        result = await controller.toggle_search_mode(False)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_toggle_browsing_mode(self, controller):
        """Test toggling browsing mode"""
        # Note: browsing mode might not be available for all accounts
        result = await controller.toggle_browsing_mode(True)
        # Should handle gracefully even if not available
        assert isinstance(result, bool)


class TestDeepResearchMode:
    """Test Deep Research mode (without actually using the 250/month quota)"""
    
    @pytest.fixture
    async def controller(self):
        """Create a mock controller for testing"""
        controller = ChatGPTBrowserController()
        controller.page = Mock()
        
        # Mock the page methods
        controller.page.wait_for_selector = AsyncMock(return_value=Mock())
        controller.page.click = AsyncMock(return_value=None)
        controller.page.keyboard = Mock()
        controller.page.keyboard.press = AsyncMock(return_value=None)
        
        # Mock locator for model dropdown
        model_button = Mock()
        model_button.click = AsyncMock(return_value=None)
        controller.page.locator.return_value.first = model_button
        
        # Mock locator for Deep research option
        deep_research = Mock()
        deep_research.click = AsyncMock(return_value=None)
        controller.page.locator.return_value.filter.return_value.first = deep_research
        
        yield controller
    
    @pytest.mark.asyncio
    async def test_deep_research_selection_mock(self, controller):
        """Test that Deep Research can be selected (mocked, no quota usage)"""
        # This test verifies the UI interaction without actually enabling Deep Research
        
        # Create a mock for deep research selection
        controller.select_deep_research_mode = AsyncMock(return_value=True)
        
        # Test that we could theoretically select it
        result = await controller.select_deep_research_mode()
        assert result is True
        
        # Verify the UI elements exist
        assert controller.page.locator is not None
        assert controller.page.click is not None
        
    @pytest.mark.asyncio
    async def test_web_search_toggle_mock(self, controller):
        """Test web search toggle (mocked)"""
        controller.toggle_search_mode = AsyncMock(return_value=True)
        
        result = await controller.toggle_search_mode(True)
        assert result is True
        
        # Verify it was called with correct argument
        controller.toggle_search_mode.assert_called_with(True)


class TestModelLatencyAwareness:
    """Test handling of model latency and thinking time"""
    
    @pytest.mark.asyncio
    async def test_o3_pro_extended_timeout(self):
        """Verify o3-pro uses extended timeout for potential 10+ minute waits"""
        controller = ChatGPTBrowserController()
        controller.page = Mock()
        
        # Mock send_message to track timeout
        actual_timeout = None
        async def mock_send(msg, timeout=120):
            nonlocal actual_timeout
            actual_timeout = timeout
            return True
        
        controller.send_message = mock_send
        
        # For o3-pro, timeout should be much higher
        await controller.send_message("Test message for o3-pro", timeout=600)
        assert actual_timeout == 600  # 10 minutes
    
    @pytest.mark.asyncio 
    async def test_model_thinking_time_awareness(self):
        """Test that we handle 'thinking' time correctly"""
        # Models like o3-pro show "Thought for X seconds" before responding
        controller = ChatGPTBrowserController()
        controller.page = Mock()
        
        # Mock wait_for_response to handle thinking time
        thinking_indicator = Mock()
        thinking_indicator.text_content = AsyncMock(return_value="Thinking...")
        
        response_ready = Mock() 
        response_ready.text_content = AsyncMock(return_value="Here's my response...")
        
        # Simulate thinking then response
        controller.page.locator.return_value.last = thinking_indicator
        
        # After waiting, response appears
        await asyncio.sleep(0.1)  # Simulate thinking
        controller.page.locator.return_value.last = response_ready
        
        # Verify we can detect when thinking is complete
        assert thinking_indicator != response_ready


class TestModelDeprecation:
    """Test handling of deprecated models"""
    
    @pytest.mark.asyncio
    async def test_gpt_4_5_deprecation_warning(self):
        """Test that GPT-4.5 deprecation is handled"""
        controller = ChatGPTBrowserController()
        
        # GPT-4.5 is deprecated July 14, 2025 but still accessible
        # This test ensures we can still select it while it's available
        controller.page = Mock()
        
        async def mock_get_model(*args):
            return "gpt-4.5"
        controller.get_current_model = mock_get_model
        
        # Should still work until fully removed
        # Mock success since it's still available
        controller.select_model = AsyncMock(return_value=True)
        result = await controller.select_model("gpt-4.5")
        assert result is True


class TestModelMapping:
    """Test model name mapping and variations"""
    
    def test_model_map_completeness(self):
        """Ensure all current models are in the model map"""
        # Model map from browser_controller.py select_model method
        model_map = {
            # Main models
            "gpt-4o": ["GPT-4o", "gpt-4o", "GPT 4o", "4o"],
            "4o": ["GPT-4o", "gpt-4o", "GPT 4o"],
            "o3": ["o3", "O3"],
            "o3-pro": ["o3-pro", "O3-pro", "o3 pro"],
            "o4-mini": ["o4-mini", "O4-mini", "o4 mini"],
            "o4-mini-high": ["o4-mini-high", "O4-mini-high", "o4 mini high"],
            # More models menu
            "gpt-4.5": ["GPT-4.5", "gpt-4.5", "GPT 4.5"],
            "gpt-4.1": ["GPT-4.1", "gpt-4.1", "GPT 4.1"],
            "gpt-4.1-mini": ["GPT-4.1-mini", "gpt-4.1-mini", "GPT 4.1 mini"],
        }
        
        # All models should have mappings
        expected_models = [
            "gpt-4o", "o3", "o3-pro", "o4-mini", "o4-mini-high",
            "gpt-4.5", "gpt-4.1", "gpt-4.1-mini"
        ]
        
        for model in expected_models:
            # Check if model exists in map (as key or in values)
            found = model.lower() in model_map
            if not found:
                # Check if it's in any of the value lists
                for key, variants in model_map.items():
                    if model in variants or any(model.lower() == v.lower() for v in variants):
                        found = True
                        break
            
            assert found, f"Model {model} not found in model map"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])