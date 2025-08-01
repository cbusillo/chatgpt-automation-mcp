#!/usr/bin/env python3
"""Comprehensive test suite for ChatGPT browser controller"""

import asyncio
import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from src.chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestChatGPTBrowserController:
    """Test suite for ChatGPT browser controller"""
    
    @pytest.fixture
    async def controller(self):
        """Create a controller instance for testing"""
        controller = ChatGPTBrowserController()
        yield controller
        if controller.browser:
            await controller.close()
    
    @pytest.mark.asyncio
    async def test_launch_and_connect(self, controller):
        """Test launching and connecting to Chrome"""
        # Test launch
        await controller.launch()
        assert controller.browser is not None
        assert controller.page is not None
        assert controller.context is not None
        
        # Test multiple launch calls (should not create new browser)
        browser1 = controller.browser
        await controller.launch()
        assert controller.browser == browser1
    
    @pytest.mark.asyncio
    async def test_chrome_launch_failure_handling(self, controller):
        """Test handling of Chrome launch failures"""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = Exception("Chrome launch failed")
            
            # Should handle the error gracefully
            with pytest.raises(Exception):
                await controller._launch_chrome_if_needed()
    
    @pytest.mark.asyncio
    async def test_model_operations(self, controller):
        """Test model selection and retrieval"""
        await controller.launch()
        
        # Mock the locator chain properly
        mock_locator = AsyncMock()
        mock_first = AsyncMock()
        mock_first.text_content = AsyncMock(return_value="GPT-4o")
        mock_locator.first = mock_first
        controller.page.locator = Mock(return_value=mock_locator)
        
        # Test get current model
        model = await controller.get_current_model()
        assert model == "GPT-4o"
        
        # Test model selection
        mock_filter = AsyncMock()
        mock_filter.click = AsyncMock()
        mock_locator.click = AsyncMock()
        mock_locator.filter = Mock(return_value=mock_filter)
        
        success = await controller.select_model("o3")
        controller.page.locator.assert_called()
    
    @pytest.mark.asyncio
    async def test_sidebar_handling(self, controller):
        """Test sidebar state detection and control"""
        await controller.launch()
        
        # Mock sidebar detection properly
        mock_locator = AsyncMock()
        
        # Test closed sidebar
        mock_locator.count = AsyncMock(return_value=0)
        controller.page.locator = Mock(return_value=mock_locator)
        is_open = await controller.is_sidebar_open()
        assert is_open is False
        
        # Test open sidebar
        mock_locator.count = AsyncMock(return_value=1)
        controller.page.locator = Mock(return_value=mock_locator)
        is_open = await controller.is_sidebar_open()
        assert is_open is True
        
        # Test toggle sidebar
        mock_keyboard = AsyncMock()
        mock_keyboard.press = AsyncMock()
        controller.page.keyboard = mock_keyboard
        
        success = await controller.toggle_sidebar(True)
        mock_keyboard.press.assert_called_with("Control+Shift+S")
    
    @pytest.mark.asyncio
    async def test_message_operations(self, controller):
        """Test sending and retrieving messages"""
        await controller.launch()
        
        # Mock page elements
        mock_locator = AsyncMock()
        mock_locator.fill = AsyncMock()
        mock_locator.press = AsyncMock()
        mock_locator.wait_for = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[])
        controller.page.locator = Mock(return_value=mock_locator)
        
        # Test send message
        await controller.send_message("Test message")
        mock_locator.fill.assert_called_with("Test message")
        mock_locator.press.assert_called_with("Enter")
        
        # Test get last response
        mock_article = Mock()
        mock_article.text_content = AsyncMock(return_value="Response text")
        controller.page.locator.return_value.all = AsyncMock(return_value=[mock_article, mock_article])
        
        response = await controller.get_last_response()
        assert response == "Response text"
    
    @pytest.mark.asyncio
    async def test_conversation_management(self, controller):
        """Test conversation listing, switching, and deletion"""
        await controller.launch()
        
        # Mock sidebar operations
        controller.is_sidebar_open = AsyncMock(return_value=False)
        controller.toggle_sidebar = AsyncMock(return_value=True)
        
        # Mock conversation elements
        controller.page.locator = AsyncMock()
        mock_conv = Mock()
        mock_conv.text_content = AsyncMock(return_value="Test Conversation")
        mock_conv.get_attribute = AsyncMock(return_value="conv-123")
        mock_conv.click = AsyncMock()
        controller.page.locator.return_value.all = AsyncMock(return_value=[mock_conv])
        
        # Test list conversations
        conversations = await controller.list_conversations()
        assert len(conversations) == 1
        assert conversations[0]["title"] == "Test Conversation"
        assert conversations[0]["id"] == "conv-123"
        
        # Verify sidebar was opened
        controller.toggle_sidebar.assert_called_with(True)
        
        # Test switch conversation
        success = await controller.switch_conversation("conv-123")
        mock_conv.click.assert_called()
        
        # Test delete conversation
        controller.page.locator.return_value.nth = AsyncMock()
        controller.page.locator.return_value.nth.return_value.click = AsyncMock()
        controller.page.keyboard = AsyncMock()
        controller.page.keyboard.press = AsyncMock()
        
        success = await controller.delete_conversation(0)
        controller.page.keyboard.press.assert_called_with("Delete")
    
    @pytest.mark.asyncio
    async def test_search_and_browsing_modes(self, controller):
        """Test search and browsing mode toggles"""
        await controller.launch()
        
        # Mock page methods
        controller.page.locator = AsyncMock()
        controller.page.locator.return_value.click = AsyncMock()
        controller.page.locator.return_value.count = AsyncMock(return_value=1)
        controller.page.locator.return_value.is_checked = AsyncMock()
        
        # Test search mode toggle
        controller.page.locator.return_value.is_checked.return_value = False
        success = await controller.toggle_search_mode(True)
        controller.page.locator.return_value.click.assert_called()
        
        # Test browsing mode toggle
        success = await controller.toggle_browsing_mode(False)
        controller.page.locator.return_value.click.assert_called()
    
    @pytest.mark.asyncio
    async def test_file_operations(self, controller):
        """Test file upload and export"""
        await controller.launch()
        
        # Mock file operations
        controller.page.locator = AsyncMock()
        controller.page.locator.return_value.set_input_files = AsyncMock()
        controller.page.locator.return_value.all = AsyncMock(return_value=[])
        
        # Test file upload
        test_file = "/tmp/test.txt"
        Path(test_file).write_text("test content")
        
        success = await controller.upload_file(test_file)
        controller.page.locator.return_value.set_input_files.assert_called_with(test_file)
        
        # Test export conversation
        mock_message = Mock()
        mock_message.text_content = AsyncMock(return_value="Test message")
        controller.page.locator.return_value.all = AsyncMock(return_value=[mock_message])
        
        content = await controller.export_conversation()
        assert "Test message" in content
        
        # Clean up
        Path(test_file).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_regenerate_response(self, controller):
        """Test response regeneration"""
        await controller.launch()
        
        # Mock page methods
        controller.page.locator = AsyncMock()
        controller.page.locator.return_value.click = AsyncMock()
        controller.page.locator.return_value.filter = AsyncMock()
        controller.page.locator.return_value.filter.return_value.click = AsyncMock()
        controller.page.keyboard = AsyncMock()
        controller.page.keyboard.press = AsyncMock()
        
        # Test regenerate
        success = await controller.regenerate_response()
        controller.page.locator.return_value.click.assert_called()
        controller.page.keyboard.press.assert_called_with("Escape")
    
    @pytest.mark.asyncio
    async def test_edit_message(self, controller):
        """Test message editing"""
        await controller.launch()
        
        # Mock page methods
        controller.page.locator = AsyncMock()
        mock_article = Mock()
        mock_article.hover = AsyncMock()
        mock_article.locator = AsyncMock()
        mock_article.locator.return_value.click = AsyncMock()
        controller.page.locator.return_value.all = AsyncMock(return_value=[mock_article])
        controller.page.locator.return_value.fill = AsyncMock()
        controller.page.locator.return_value.press = AsyncMock()
        
        # Test edit
        success = await controller.edit_message(0, "New content")
        mock_article.hover.assert_called()
        mock_article.locator.return_value.click.assert_called()
        controller.page.locator.return_value.fill.assert_called_with("New content")
    
    @pytest.mark.asyncio
    async def test_wait_for_response(self, controller):
        """Test waiting for response completion"""
        await controller.launch()
        
        # Mock response detection
        controller.page.locator = AsyncMock()
        
        # Test immediate completion
        controller.page.locator.return_value.count = AsyncMock(return_value=0)
        completed = await controller.wait_for_response(timeout=1)
        assert completed is True
        
        # Test timeout
        controller.page.locator.return_value.count = AsyncMock(return_value=1)
        completed = await controller.wait_for_response(timeout=0.1)
        assert completed is False
    
    @pytest.mark.asyncio
    async def test_error_handling(self, controller):
        """Test error handling in various scenarios"""
        # Test without launching
        model = await controller.get_current_model()
        assert model is None
        
        # Test with page errors
        await controller.launch()
        controller.page.locator = Mock(side_effect=Exception("Page error"))
        
        model = await controller.get_current_model()
        assert model is None
        
        response = await controller.get_last_response()
        assert response is None
        
        success = await controller.send_message("Test")
        assert success is True  # Should not raise
    
    @pytest.mark.asyncio 
    async def test_batch_operations(self, controller):
        """Test batch operations execution"""
        await controller.launch()
        
        # Mock page methods
        controller.send_message = AsyncMock(return_value=True)
        controller.get_last_response = AsyncMock(return_value="Response")
        controller.select_model = AsyncMock(return_value=True)
        
        # Test batch execution
        operations = [
            {"operation": "send_message", "args": {"message": "Test"}},
            {"operation": "get_last_response", "args": {}},
            {"operation": "select_model", "args": {"model": "gpt-4"}}
        ]
        
        results = await controller.batch_operations(operations)
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["result"] == "Response"
        assert results[2]["success"] is True
        
        # Test with error and continue_on_error
        controller.send_message = AsyncMock(side_effect=Exception("Test error"))
        operations = [
            {"operation": "send_message", "args": {"message": "Test"}, "continue_on_error": True},
            {"operation": "get_last_response", "args": {}}
        ]
        
        results = await controller.batch_operations(operations)
        assert len(results) == 2
        assert results[0]["success"] is False
        assert "Test error" in results[0]["error"]
        assert results[1]["success"] is True


@pytest.mark.asyncio
async def test_edge_cases():
    """Test various edge cases"""
    controller = ChatGPTBrowserController()
    
    try:
        # Test empty message
        await controller.launch()
        success = await controller.send_message("")
        assert success is True  # Should handle gracefully
        
        # Test invalid model
        controller.page.locator = AsyncMock()
        controller.page.locator.return_value.click = AsyncMock()
        controller.page.locator.return_value.filter = AsyncMock()
        controller.page.locator.return_value.filter.return_value.click = AsyncMock(side_effect=Exception("Not found"))
        
        success = await controller.select_model("invalid-model")
        assert success is False
        
        # Test conversation switching with sidebar closed then opened
        controller.is_sidebar_open = AsyncMock(side_effect=[False, True])
        controller.toggle_sidebar = AsyncMock(return_value=True)
        controller.page.locator.return_value.all = AsyncMock(return_value=[])
        
        conversations = await controller.list_conversations()
        assert conversations == []
        controller.toggle_sidebar.assert_called()
        
    finally:
        await controller.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])