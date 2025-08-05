#!/usr/bin/env python3
"""
Test actual ChatGPT UI automation with all July 2025 models
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def test_model_selection():
    """Test selecting each model in ChatGPT UI"""
    controller = ChatGPTBrowserController()
    
    # Main models that should be available to all Pro users
    main_models = ["gpt-4o", "o3", "o3-pro", "o4-mini", "o4-mini-high"]
    
    # Additional models in "More models" menu
    more_models = ["gpt-4.5", "gpt-4.1", "gpt-4.1-mini"]
    
    try:
        print("🚀 Launching ChatGPT...")
        await controller.launch()
        await asyncio.sleep(3)  # Wait for page to load
        
        # Check if ready
        if not await controller.is_ready():
            print("❌ ChatGPT not ready")
            return
        
        print("✅ ChatGPT ready")
        
        # Start a new chat
        print("\n📝 Starting new chat...")
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Test main models
        print("\n🔍 Testing main models...")
        successful_models = []
        failed_models = []
        
        for model in main_models:
            print(f"\n  Testing {model}...")
            try:
                success = await controller.select_model(model)
                if success:
                    # Verify selection
                    current = await controller.get_current_model()
                    if current and model in current.lower():
                        print(f"  ✅ {model} selected successfully")
                        successful_models.append(model)
                    else:
                        print(f"  ⚠️ {model} selection uncertain - current: {current}")
                        failed_models.append((model, f"current: {current}"))
                else:
                    print(f"  ❌ {model} failed to select")
                    failed_models.append((model, "selection failed"))
                
                await asyncio.sleep(1)  # Brief pause between selections
                
            except Exception as e:
                print(f"  ❌ {model} error: {str(e)}")
                failed_models.append((model, str(e)))
        
        # Test additional models (these might not be available to all users)
        print("\n🔍 Testing additional models (may not be available)...")
        for model in more_models:
            print(f"\n  Testing {model}...")
            try:
                success = await controller.select_model(model)
                if success:
                    current = await controller.get_current_model()
                    if current and model in current.lower():
                        print(f"  ✅ {model} selected successfully")
                        successful_models.append(model)
                    else:
                        print(f"  ⚠️ {model} may not be available - current: {current}")
                else:
                    print(f"  ℹ️ {model} not available (expected for most users)")
                
                await asyncio.sleep(get_delay("ui_update"))
                
            except Exception as e:
                print(f"  ℹ️ {model} not available: {str(e)}")
        
        # Summary
        print("\n📊 Summary:")
        print(f"  ✅ Successful models: {', '.join(successful_models)}")
        if failed_models:
            print(f"  ❌ Failed models:")
            for model, reason in failed_models:
                print(f"     - {model}: {reason}")
        
        # Test a simple message with the current model
        print("\n💬 Testing message send...")
        current_model = await controller.get_current_model()
        print(f"  Current model: {current_model}")
        
        response = await controller.send_and_get_response(
            "Say 'Hello from automation test!' in exactly 5 words.",
            timeout=60
        )
        
        if response:
            print(f"  ✅ Response received: {response[:100]}...")
        else:
            print("  ❌ No response received")
        
        # Test conversation operations
        print("\n🗂️ Testing conversation operations...")
        
        # Get conversation
        conversation = await controller.get_conversation()
        print(f"  Messages in conversation: {len(conversation)}")
        
        # List conversations
        conversations = await controller.list_conversations()
        print(f"  Total conversations: {len(conversations) if conversations else 0}")
        
        # Save conversation
        filename = await controller.save_conversation("test_model_selection", "markdown")
        if filename:
            print(f"  ✅ Conversation saved to: {filename}")
        else:
            print("  ❌ Failed to save conversation")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔚 Closing browser...")
        await controller.close()


async def test_advanced_features():
    """Test advanced features like search mode and quota tracking"""
    controller = ChatGPTBrowserController()
    
    try:
        print("🚀 Testing advanced features...")
        await controller.launch()
        await asyncio.sleep(3)
        
        if not await controller.is_ready():
            print("❌ ChatGPT not ready")
            return
        
        # New chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Test web search toggle (should not consume quota in test)
        print("\n🔍 Testing web search toggle...")
        success = await controller.toggle_search_mode(True)
        print(f"  Enable search: {'✅' if success else '❌'}")
        
        if success:
            # Send a search query (but keep it simple to not use quota)
            print("  Sending test query (not using actual search)...")
            await controller.send_message("What is 2+2? (no search needed)")
            await asyncio.sleep(2)
            
            # Disable search
            success = await controller.toggle_search_mode(False)
            print(f"  Disable search: {'✅' if success else '❌'}")
        
        # Test response timing with o3
        print("\n⏱️ Testing response timing with reasoning model...")
        await controller.select_model("o3")
        await asyncio.sleep(get_delay("ui_update"))
        
        import time
        start_time = time.time()
        
        # Send a message that requires some thinking
        await controller.send_message("What are the prime factors of 91?")
        
        # Wait for thinking to complete
        print("  Waiting for response (o3 may think for a bit)...")
        success = await controller.wait_for_response(timeout=120)
        
        elapsed = time.time() - start_time
        print(f"  Response complete: {'✅' if success else '❌'}")
        print(f"  Total time: {elapsed:.1f} seconds")
        
        if success:
            response = await controller.get_last_response()
            if response:
                print(f"  Response: {response[:100]}...")
        
        print("\n✅ Advanced features test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def main():
    """Run all tests"""
    print("🧪 ChatGPT Automation UI Tests")
    print("================================\n")
    
    # Test 1: Model selection
    await test_model_selection()
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Advanced features
    await test_advanced_features()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())