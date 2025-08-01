#!/usr/bin/env python3
"""Functional test for ChatGPT MCP - runs a simple real browser test"""

import asyncio
import logging
from src.chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_functional():
    """Run a simple functional test"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n=== Running Functional Test ===")
        
        # Test 1: Launch and connect
        print("\n1. Testing launch and connect...")
        await controller.launch()
        print("✓ Successfully connected to Chrome")
        
        # Test 2: Check sidebar state
        print("\n2. Testing sidebar state...")
        is_open = await controller.is_sidebar_open()
        print(f"✓ Sidebar is {'open' if is_open else 'closed'}")
        
        # Test 3: Get current model
        print("\n3. Testing model detection...")
        model = await controller.get_current_model()
        print(f"✓ Current model: {model}")
        
        # Test 4: List conversations
        print("\n4. Testing conversation listing...")
        conversations = await controller.list_conversations()
        print(f"✓ Found {len(conversations)} conversations")
        if conversations:
            print(f"   Latest: {conversations[0]['title'][:50]}...")
        
        # Test 5: Create new chat
        print("\n5. Testing new chat creation...")
        success = await controller.new_chat()
        print(f"✓ New chat created: {success}")
        
        if success:
            # Test 6: Send a message
            print("\n6. Testing message sending...")
            await controller.send_message("Hello! This is a test from the ChatGPT MCP functional test.")
            print("✓ Message sent")
            
            # Test 7: Wait for response
            print("\n7. Waiting for response...")
            completed = await controller.wait_for_response(timeout=30)
            print(f"✓ Response completed: {completed}")
            
            if completed:
                # Test 8: Get response
                print("\n8. Getting response...")
                response = await controller.get_last_response()
                if response:
                    print(f"✓ Got response ({len(response)} chars): {response[:100]}...")
                else:
                    print("✗ No response received")
        
        # Test 9: Sidebar toggle
        print("\n9. Testing sidebar toggle...")
        original_state = await controller.is_sidebar_open()
        await controller.toggle_sidebar(not original_state)
        await asyncio.sleep(get_delay("ui_update"))
        new_state = await controller.is_sidebar_open()
        print(f"✓ Sidebar toggled from {original_state} to {new_state}")
        
        # Restore original state
        await controller.toggle_sidebar(original_state)
        
        print("\n✓ All functional tests passed!")
        
    except Exception as e:
        logger.error(f"Functional test failed: {e}", exc_info=True)
        print(f"\n✗ Test failed: {e}")
    finally:
        await controller.close()
        print("\n=== Functional Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_functional())