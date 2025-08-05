#!/usr/bin/env python3
"""
Test the fixes for ChatGPT UI automation based on screenshots
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def test_gpt4o_default():
    """Test that GPT-4o is handled as default model"""
    controller = ChatGPTBrowserController()
    
    try:
        print("🚀 Testing GPT-4o default handling...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Check current model
        current = await controller.get_current_model()
        print(f"  Current model: {current}")
        
        # Try to select GPT-4o (should recognize it's already selected)
        success = await controller.select_model("gpt-4o")
        print(f"  Select GPT-4o: {'✅' if success else '❌'}")
        
    finally:
        await controller.close()


async def test_more_models_menu():
    """Test accessing models in 'More models' submenu"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n🚀 Testing 'More models' submenu...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Start new chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Try to select GPT-4.5 (in More models menu)
        print("  Attempting to select GPT-4.5...")
        success = await controller.select_model("gpt-4.5")
        print(f"  Select GPT-4.5: {'✅' if success else '❌'}")
        
        if success:
            current = await controller.get_current_model()
            print(f"  Current model after selection: {current}")
        
    finally:
        await controller.close()


async def test_tools_menu():
    """Test Tools menu features (Deep Research, Web Search)"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n🚀 Testing Tools menu features...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Test quota check
        print("  Checking Deep Research quota...")
        quota = await controller.get_quota_remaining("deep_research")
        if quota:
            print(f"  ✅ Deep Research quota: {quota} remaining")
        else:
            print("  ❌ Could not get quota")
        
        # Test web search toggle
        print("\n  Testing Web Search toggle...")
        success = await controller.toggle_search_mode(True)
        print(f"  Toggle Web Search: {'✅' if success else '❌'}")
        
        # Test Deep Research enable (but don't actually use it)
        print("\n  Testing Deep Research enable (UI only)...")
        # Just test the UI interaction, don't send a message
        success = await controller.enable_deep_research()
        print(f"  Enable Deep Research: {'✅' if success else '❌'}")
        
        if success:
            print("  ⚠️ Deep Research enabled - closing without using quota")
            # Start new chat to exit Deep Research mode
            await controller.new_chat()
        
    finally:
        await controller.close()


async def test_model_detection():
    """Test improved model detection"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n🚀 Testing model detection...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Test different models
        models_to_test = ["o4-mini", "o3", "o4-mini-high"]
        
        for model in models_to_test:
            print(f"\n  Testing {model}...")
            success = await controller.select_model(model)
            
            if success:
                current = await controller.get_current_model()
                print(f"  ✅ Selected: {model}, Current: {current}")
            else:
                print(f"  ❌ Failed to select {model}")
            
            await asyncio.sleep(get_delay("ui_update"))
        
    finally:
        await controller.close()


async def main():
    """Run all UI fix tests"""
    print("🧪 ChatGPT UI Fix Tests")
    print("=" * 50)
    
    # Test 1: GPT-4o default handling
    await test_gpt4o_default()
    
    # Test 2: More models menu
    await test_more_models_menu()
    
    # Test 3: Tools menu
    await test_tools_menu()
    
    # Test 4: Model detection
    await test_model_detection()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())