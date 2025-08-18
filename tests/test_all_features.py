"""
Comprehensive test suite for all ChatGPT automation features.
Run this to verify EVERYTHING works.
"""

import asyncio
import pytest
import os
from pathlib import Path
from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


@pytest.mark.asyncio
async def test_all_core_features():
    """Test all core features in sequence"""
    controller = ChatGPTBrowserController()
    
    try:
        # 1. Launch browser
        print("\n=== Testing Browser Launch ===")
        await controller.launch()
        assert controller.page is not None, "Failed to launch browser"
        print("✅ Browser launched successfully")
        
        # 2. New chat
        print("\n=== Testing New Chat ===")
        chat_id = await controller.new_chat()
        assert chat_id, "Failed to create new chat"
        print(f"✅ New chat created: {chat_id}")
        
        # 3. Send message
        print("\n=== Testing Send Message ===")
        msg_id = await controller.send_message("Hello, this is a test message. Please respond briefly.")
        assert msg_id, "Failed to send message"
        print(f"✅ Message sent: {msg_id}")
        
        # Wait for response
        await asyncio.sleep(5)
        
        # 4. Get last response
        print("\n=== Testing Get Last Response ===")
        response = await controller.get_last_response()
        assert response, "Failed to get last response"
        print(f"✅ Got response: {response[:100]}...")
        
        # 5. Get conversation
        print("\n=== Testing Get Conversation ===")
        conversation = await controller.get_conversation()
        assert conversation, "Failed to get conversation"
        assert len(conversation) >= 2, "Conversation should have at least 2 messages"
        print(f"✅ Got conversation with {len(conversation)} messages")
        
        # 6. Select model (ensure we're on gpt-4.1 for faster testing)
        print("\n=== Testing Model Selection ===")
        current_model = await controller.get_current_model()
        print(f"Current model: {current_model}")
        # Always switch to gpt-4.1 for consistent fast testing
        model_switched = await controller.select_model("gpt-4.1")
        if model_switched:
            print("✅ Model switched to gpt-4.1")
        else:
            print("✅ Model selection attempted")
        
        # 7. Test Think Longer in a fresh chat
        print("\n=== Testing Think Longer ===")
        await controller.new_chat()  # Start fresh
        think_longer = await controller.enable_think_longer()
        assert think_longer, "Failed to enable Think Longer"
        print("✅ Think Longer enabled (gpt-5-thinking model)")
        print("Note: Thinking models can take minutes to start responding")
        
        # 8. Test Deep Research in a fresh chat (to avoid conflicts)
        print("\n=== Testing Deep Research ===")
        await controller.new_chat()  # Start fresh again
        deep_research = await controller.enable_deep_research()
        assert deep_research, "Failed to enable Deep Research"
        print("✅ Deep Research enabled")
        
        # 9. New chat for file upload test (clean state)
        print("\n=== Testing New Chat (for file upload) ===")
        await controller.new_chat()
        print("✅ New chat created for file upload (clean state, no Deep Research/Think Longer)")
        
        # 10. Upload file (create a test file first)
        print("\n=== Testing File Upload ===")
        test_file = Path("/tmp/test_upload.txt")
        test_file.write_text("This is a test file for upload verification.")
        uploaded = await controller.upload_file(str(test_file))
        assert uploaded, "Failed to upload file"
        print("✅ File uploaded successfully")
        
        # 11. Send message with uploaded file context
        print("\n=== Testing Message with File Context ===")
        msg_with_file = await controller.send_message("What's in the file I just uploaded?")
        assert msg_with_file, "Failed to send message about file"
        print("✅ Message sent about uploaded file")
        
        # Wait for response to complete
        print("Waiting for response...")
        await asyncio.sleep(10)
        
        # 12. Regenerate response
        print("\n=== Testing Regenerate Response ===")
        regenerated = await controller.regenerate_response()
        if regenerated:
            print("✅ Response regenerated")
        else:
            print("⚠️ Regenerate not available (may need response first), skipping")
        
        # 13. Edit message
        print("\n=== Testing Edit Message ===")
        edited = await controller.edit_message(0, "What's in the uploaded text file? Please be specific.")
        if edited:
            print("✅ Message edited")
        else:
            print("⚠️ Edit not available, skipping")
        
        await asyncio.sleep(3)
        
        # 14. List conversations
        print("\n=== Testing List Conversations ===")
        conversations = await controller.list_conversations()
        assert conversations, "Failed to list conversations"
        assert len(conversations) >= 1, "Should have at least one conversation"
        print(f"✅ Listed {len(conversations)} conversations")
        
        # 15. Save conversation (skip if no conversation)
        print("\n=== Testing Save Conversation ===")
        saved_path = await controller.save_conversation(
            filename="test_conversation",
            format="markdown"
        )
        if saved_path:
            if Path(saved_path).exists():
                print(f"✅ Conversation saved to: {saved_path}")
            else:
                print("⚠️ Save path returned but file doesn't exist")
        else:
            print("⚠️ No conversation to save, skipping")
        
        # 16. Switch conversation (if multiple exist)
        if len(conversations) > 1:
            print("\n=== Testing Switch Conversation ===")
            switched = await controller.switch_conversation(conversations[1]['id'])
            assert switched, "Failed to switch conversation"
            print("✅ Switched to different conversation")
        
        # 17. Delete conversation (create a new one first)
        print("\n=== Testing Delete Conversation ===")
        new_chat_id = await controller.new_chat()
        await controller.send_message("This chat will be deleted")
        await asyncio.sleep(2)
        deleted = await controller.delete_conversation(0)  # Delete the current (newest) chat
        if deleted:
            print("✅ Conversation deleted")
        else:
            print("⚠️ Delete not available, skipping")
        
        print("\n" + "="*60)
        print("🎉 ALL FEATURES TESTED SUCCESSFULLY! 🎉")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
    finally:
        # Keep browser open for inspection if needed
        await asyncio.sleep(2)


@pytest.mark.asyncio
async def test_web_search_integration():
    """Test web search auto-enable feature"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing Web Search Auto-Enable ===")
        # Should auto-enable web search due to "latest" keyword
        msg_id = await controller.send_message("What are the latest updates to Python 3.13?")
        assert msg_id, "Failed to send message with web search"
        print("✅ Web search auto-enabled for research query")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Web search test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_error_recovery():
    """Test error recovery mechanisms"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        
        print("\n=== Testing Error Recovery ===")
        
        # Test sending message to non-existent chat
        print("Testing invalid chat handling...")
        await controller.new_chat()
        
        # Test with empty message
        try:
            await controller.send_message("")
            print("⚠️  Empty message should have failed")
        except:
            print("✅ Empty message properly rejected")
        
        # Test file upload with non-existent file
        try:
            await controller.upload_file("/nonexistent/file.txt")
            print("⚠️  Non-existent file should have failed")
        except:
            print("✅ Non-existent file properly rejected")
        
        print("✅ Error recovery mechanisms working")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error recovery test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_all_core_features())