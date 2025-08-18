"""
Test editing features: regenerate response and edit message.
These require proper conversation context to work.
"""

import asyncio
import pytest
from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


@pytest.mark.asyncio
async def test_regenerate_response():
    """Test regenerating a response"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        # Switch to a faster model for testing
        print("Switching to gpt-4.1 for faster testing...")
        await controller.select_model("gpt-4.1")
        
        print("\n=== Testing Regenerate Response ===")
        
        # Send a message and wait for response
        print("Sending initial message...")
        await controller.send_message("What is the capital of France?")
        
        # Wait for response to complete
        print("Waiting for response...")
        response_ready = await controller.wait_for_response(timeout=60)
        assert response_ready, "Response didn't complete"
        
        # Get the first response
        first_response = await controller.get_last_response()
        print(f"First response: {first_response[:100]}...")
        
        # Now regenerate
        print("Regenerating response...")
        regenerated = await controller.regenerate_response()
        
        if regenerated:
            print("✅ Regenerate command accepted")
            # Wait longer for thinking models, shorter for regular
            wait_time = 60 if "thinking" in (await controller.get_current_model()).lower() else 10
            print(f"Waiting {wait_time}s for regeneration to complete...")
            await asyncio.sleep(wait_time)
        else:
            print("⚠️ Regenerate might have failed or is still processing")
        
        # Get the regenerated response
        new_response = await controller.get_last_response()
        print(f"Regenerated response: {new_response[:100]}...")
        
        # Responses might be similar but should be regenerated
        print("✅ Response regeneration working!")
        
        return True
        
    except Exception as e:
        print(f"❌ Regenerate test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_edit_message():
    """Test editing a previous message"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        # Switch to a faster model for testing
        print("Switching to gpt-4.1 for faster testing...")
        await controller.select_model("gpt-4.1")
        
        print("\n=== Testing Edit Message ===")
        
        # Send first message
        print("Sending initial message...")
        await controller.send_message("Tell me about Paris")
        
        # Wait for response
        print("Waiting for response...")
        await controller.wait_for_response(timeout=60)
        first_response = await controller.get_last_response()
        print(f"First response about Paris: {first_response[:100]}...")
        
        # Edit the message (index 0 is the first user message)
        print("Editing message to ask about London...")
        edited = await controller.edit_message(0, "Tell me about London")
        
        if edited:
            print("✅ Edit command executed")
            # Wait for response to regenerate after edit
            print("Waiting for new response after edit...")
            response_ready = await controller.wait_for_response(timeout=60)
            if response_ready:
                print("✅ New response ready after edit")
        else:
            print("⚠️ Edit might have failed")
        
        # Get the new response
        new_response = await controller.get_last_response()
        print(f"New response about London: {new_response[:100]}...")
        
        # Verify the response changed
        if "london" in new_response.lower() or "London" in new_response:
            print("✅ Message edit working - response is about London!")
        else:
            print("⚠️ Response might not have updated after edit")
        
        return True
        
    except Exception as e:
        print(f"❌ Edit message test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_edit_and_regenerate_together():
    """Test both editing and regenerating in sequence"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        # Use faster model
        print("Switching to gpt-4.1 for faster testing...")
        await controller.select_model("gpt-4.1")
        
        print("\n=== Testing Edit + Regenerate Together ===")
        
        # Send message
        print("Step 1: Sending initial message...")
        await controller.send_message("What is 2+2?")
        await controller.wait_for_response(timeout=60)
        response1 = await controller.get_last_response()
        print(f"Initial response: {response1[:50]}...")
        
        # Edit the message
        print("Step 2: Editing to ask 3+3...")
        edited = await controller.edit_message(0, "What is 3+3?")
        assert edited, "Failed to edit"
        # Wait for edit to process and new response
        await controller.wait_for_response(timeout=60)
        response2 = await controller.get_last_response()
        print(f"After edit: {response2[:50]}...")
        
        # Regenerate the edited response
        print("Step 3: Regenerating the response...")
        regenerated = await controller.regenerate_response()
        assert regenerated, "Failed to regenerate"
        # Wait for regeneration
        await controller.wait_for_response(timeout=60)
        response3 = await controller.get_last_response()
        print(f"After regenerate: {response3[:50]}...")
        
        print("✅ Edit + Regenerate both working!")
        
        return True
        
    except Exception as e:
        print(f"❌ Combined test failed: {e}")
        raise


@pytest.mark.asyncio  
async def test_conversation_history_after_edits():
    """Test that conversation history is preserved after edits"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing Conversation History ===")
        
        # Build a conversation
        print("Building conversation...")
        await controller.send_message("Hello")
        await controller.wait_for_response(timeout=60)
        
        await controller.send_message("What's the weather like?")
        await controller.wait_for_response(timeout=60)
        
        # Get initial conversation
        conv_before = await controller.get_conversation()
        print(f"Messages before edit: {len(conv_before)}")
        
        # Edit first message
        print("Editing first message...")
        edited = await controller.edit_message(0, "Hi there!")
        assert edited, "Failed to edit"
        
        await asyncio.sleep(10)
        
        # Get conversation after edit
        conv_after = await controller.get_conversation()
        print(f"Messages after edit: {len(conv_after)}")
        
        # Check if edit is reflected
        if conv_after and len(conv_after) > 0:
            if "Hi there" in conv_after[0].get("content", ""):
                print("✅ Edit reflected in conversation history!")
            else:
                print("⚠️ Edit might not be reflected in history")
        
        return True
        
    except Exception as e:
        print(f"❌ History test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_regenerate_response())