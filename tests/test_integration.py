#!/usr/bin/env python3
"""Integration tests for ChatGPT MCP - tests actual browser automation"""

import asyncio
import pytest
import logging
from pathlib import Path
from datetime import datetime
from src.chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Skip these tests by default since they require a real browser
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--integration", default=False),
    reason="Integration tests require --integration flag"
)


class TestChatGPTIntegration:
    """Integration tests with real browser"""
    
    @pytest.fixture
    async def controller(self):
        """Create a real controller instance"""
        controller = ChatGPTBrowserController()
        yield controller
        await controller.close()
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, controller):
        """Test a complete conversation flow"""
        # Launch browser
        await controller.launch()
        assert controller.page is not None
        
        # Start new chat
        success = await controller.new_chat()
        assert success is True
        
        # Send message
        test_message = f"Integration test at {datetime.now()}"
        await controller.send_message(test_message)
        
        # Wait for response
        completed = await controller.wait_for_response(timeout=30)
        assert completed is True
        
        # Get response
        response = await controller.get_last_response()
        assert response is not None
        assert len(response) > 0
        
        # Get full conversation
        conversation = await controller.get_conversation()
        assert len(conversation) >= 2
        assert conversation[0]["role"] == "user"
        assert test_message in conversation[0]["content"]
    
    @pytest.mark.asyncio
    async def test_sidebar_state_handling(self, controller):
        """Test sidebar open/closed state handling"""
        await controller.launch()
        
        # Check initial state
        initial_state = await controller.is_sidebar_open()
        logger.info(f"Initial sidebar state: {initial_state}")
        
        # Toggle to opposite state
        success = await controller.toggle_sidebar(not initial_state)
        assert success is True
        await asyncio.sleep(1)
        
        # Verify state changed
        new_state = await controller.is_sidebar_open()
        assert new_state != initial_state
        
        # Test conversation listing with sidebar
        if not new_state:
            # Open sidebar for listing
            await controller.toggle_sidebar(True)
        
        conversations = await controller.list_conversations()
        assert isinstance(conversations, list)
        
        # Restore original state
        await controller.toggle_sidebar(initial_state)
    
    @pytest.mark.asyncio
    async def test_model_switching(self, controller):
        """Test switching between models"""
        await controller.launch()
        
        # Get current model
        current_model = await controller.get_current_model()
        logger.info(f"Current model: {current_model}")
        
        # Define test models
        test_models = ["gpt-4", "gpt-4o", "o3-mini"]
        
        for model in test_models:
            if model != current_model:
                # Switch to different model
                success = await controller.select_model(model)
                if success:
                    await asyncio.sleep(2)
                    new_model = await controller.get_current_model()
                    logger.info(f"Switched to: {new_model}")
                    break
        
        # Switch back to original
        if current_model:
            await controller.select_model(current_model)
    
    @pytest.mark.asyncio
    async def test_search_mode_toggle(self, controller):
        """Test search mode toggle functionality"""
        await controller.launch()
        
        # Enable search mode
        success = await controller.toggle_search_mode(True)
        logger.info(f"Enable search mode: {success}")
        
        if success:
            # Send a search query
            await controller.send_message("What's the weather today in San Francisco?")
            await controller.wait_for_response(timeout=30)
            
            response = await controller.get_last_response()
            assert response is not None
            
            # Disable search mode
            await controller.toggle_search_mode(False)
    
    @pytest.mark.asyncio
    async def test_message_editing(self, controller):
        """Test editing messages"""
        await controller.launch()
        await controller.new_chat()
        
        # Send initial message
        await controller.send_message("Original message for editing test")
        await controller.wait_for_response(timeout=20)
        
        # Edit the message
        success = await controller.edit_message(0, "Edited message content")
        assert success is True
        
        # Wait for new response
        await controller.wait_for_response(timeout=20)
        
        # Verify conversation updated
        conversation = await controller.get_conversation()
        assert "Edited message content" in conversation[0]["content"]
    
    @pytest.mark.asyncio
    async def test_regenerate_response(self, controller):
        """Test regenerating responses"""
        await controller.launch()
        await controller.new_chat()
        
        # Send message
        await controller.send_message("Tell me a random fact")
        await controller.wait_for_response(timeout=20)
        
        # Get first response
        first_response = await controller.get_last_response()
        
        # Regenerate
        success = await controller.regenerate_response()
        assert success is True
        
        await controller.wait_for_response(timeout=20)
        
        # Get regenerated response
        second_response = await controller.get_last_response()
        
        # Responses should be different
        assert first_response != second_response
    
    @pytest.mark.asyncio
    async def test_file_upload(self, controller):
        """Test file upload functionality"""
        await controller.launch()
        await controller.new_chat()
        
        # Create test file
        test_file = Path("/tmp/test_upload.txt")
        test_file.write_text("This is a test file for ChatGPT upload integration test.")
        
        try:
            # Upload file
            success = await controller.upload_file(str(test_file))
            assert success is True
            
            # Send message about the file
            await controller.send_message("What's in the uploaded file?")
            await controller.wait_for_response(timeout=30)
            
            response = await controller.get_last_response()
            assert "test file" in response.lower()
            
        finally:
            test_file.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_export_and_save(self, controller):
        """Test exporting and saving conversations"""
        await controller.launch()
        await controller.new_chat()
        
        # Create a conversation
        await controller.send_message("Test message for export")
        await controller.wait_for_response(timeout=20)
        
        # Export as markdown
        markdown = await controller.export_conversation("markdown")
        assert "Test message for export" in markdown
        assert "## User" in markdown
        assert "## ChatGPT" in markdown
        
        # Export as JSON
        json_export = await controller.export_conversation("json")
        assert isinstance(json_export, str)
        
        # Save to file
        filename = await controller.save_conversation()
        assert filename is not None
        assert Path(filename).exists()
        
        # Clean up
        Path(filename).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_conversation_management(self, controller):
        """Test listing, switching, and deleting conversations"""
        await controller.launch()
        
        # Create a test conversation
        await controller.new_chat()
        test_id = f"Integration test {datetime.now().strftime('%H:%M:%S')}"
        await controller.send_message(f"Test conversation: {test_id}")
        await controller.wait_for_response(timeout=20)
        
        # List conversations
        conversations = await controller.list_conversations()
        assert len(conversations) > 0
        
        # Find our test conversation
        test_conv = None
        for i, conv in enumerate(conversations):
            if test_id in conv.get("title", ""):
                test_conv = (i, conv)
                break
        
        if test_conv:
            # Switch to a different conversation
            if len(conversations) > 1:
                other_idx = 0 if test_conv[0] != 0 else 1
                success = await controller.switch_conversation(other_idx)
                assert success is True
                
                # Switch back
                await asyncio.sleep(1)
                success = await controller.switch_conversation(test_conv[0])
                assert success is True
            
            # Delete the test conversation
            success = await controller.delete_conversation(test_conv[0])
            assert success is True
    
    @pytest.mark.asyncio
    async def test_batch_operations(self, controller):
        """Test batch operations"""
        await controller.launch()
        
        # Execute multiple operations
        operations = [
            {"operation": "new_chat"},
            {"operation": "send_message", "args": {"message": "Batch operation test"}},
            {"operation": "wait_for_response", "args": {"timeout": 20}},
            {"operation": "get_last_response"},
            {"operation": "get_current_model"},
        ]
        
        results = await controller.batch_operations(operations)
        
        # Verify results
        assert len(results) == 5
        assert results[0]["success"] is True  # new_chat
        assert results[1]["success"] is True  # send_message
        assert results[2]["success"] is True  # wait_for_response
        assert results[3]["success"] is True  # get_last_response
        assert results[3]["result"] is not None
        assert results[4]["success"] is True  # get_current_model
        assert results[4]["result"] is not None


@pytest.mark.asyncio
async def test_error_recovery():
    """Test error recovery mechanisms"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        
        # Test recovery from navigation issues
        controller.page.goto = asyncio.coroutine(lambda url: None)
        
        # Should still work
        success = await controller.new_chat()
        # May fail but shouldn't crash
        
        # Test recovery from selector changes
        original_send = controller.send_message
        
        async def failing_send(msg):
            # Simulate selector not found
            raise Exception("Selector not found")
        
        controller.send_message = failing_send
        
        # Should handle gracefully
        await controller.send_message("Test")
        
        # Restore and verify recovery
        controller.send_message = original_send
        await controller.send_message("Recovery test")
        
    finally:
        await controller.close()


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require a real browser"
    )


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_integration.py --integration -v
    pytest.main([__file__, "--integration", "-v"])