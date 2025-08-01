#!/usr/bin/env python3
"""
Test More models submenu with improved implementation
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def test_more_models_improved():
    """Test More models submenu with improved selectors"""
    controller = ChatGPTBrowserController()
    
    try:
        print("🚀 Testing improved More models submenu...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Start new chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Test GPT-4.1 selection
        print("\n📋 Testing GPT-4.1 selection...")
        
        # First check current model
        current = await controller.get_current_model()
        print(f"  Current model: {current}")
        
        # Try to select GPT-4.1
        success = await controller.select_model("gpt-4.1")
        print(f"  Selection result: {'✅' if success else '❌'}")
        
        if success:
            # Verify selection
            new_model = await controller.get_current_model()
            print(f"  New model: {new_model}")
            
            # Test sending a message with GPT-4.1
            print("\n  Testing message with GPT-4.1...")
            response = await controller.send_and_get_response(
                "What model are you using? Please confirm you are GPT-4.1.",
                timeout=60
            )
            if response:
                print(f"  Response preview: {response[:100]}...")
        
        # Test GPT-4.5 selection
        print("\n📋 Testing GPT-4.5 selection...")
        success = await controller.select_model("gpt-4.5")
        print(f"  Selection result: {'✅' if success else '❌'}")
        
        if success:
            new_model = await controller.get_current_model()
            print(f"  New model: {new_model}")
        
        # Test GPT-4.1-mini selection
        print("\n📋 Testing GPT-4.1-mini selection...")
        success = await controller.select_model("gpt-4.1-mini")
        print(f"  Selection result: {'✅' if success else '❌'}")
        
        if success:
            new_model = await controller.get_current_model()
            print(f"  New model: {new_model}")
        
        # Test switching back to main model
        print("\n📋 Testing switch back to main model (o4-mini-high)...")
        success = await controller.select_model("o4-mini-high")
        print(f"  Selection result: {'✅' if success else '❌'}")
        
        if success:
            new_model = await controller.get_current_model()
            print(f"  New model: {new_model}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def debug_model_picker_structure():
    """Debug the model picker menu structure"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n\n🔍 Debugging model picker structure...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Open model picker
        print("\n📋 Opening model picker...")
        picker_button = controller.page.locator('[data-testid="model-switcher-dropdown-button"]').first
        if await picker_button.count() > 0:
            await picker_button.click()
            await asyncio.sleep(1)
            print("  ✅ Opened model picker")
            
            # Look for all menu items
            print("\n📋 Analyzing menu structure...")
            
            # Method 1: Look for all div[role="menuitem"]
            menu_items = controller.page.locator('div[role="menuitem"]')
            count = await menu_items.count()
            print(f"\n  Method 1 - Found {count} menu items (div[role='menuitem']):")
            
            for i in range(count):
                item = menu_items.nth(i)
                text = await item.text_content()
                # Check if it has children (submenu indicator)
                has_children = await item.locator('svg').count() > 0
                print(f"    {i}: '{text.strip()}' {' (has submenu)' if has_children else ''}")
            
            # Method 2: Look for specific text
            print("\n  Method 2 - Looking for specific items:")
            specific_items = ["More models", "GPT-4.1", "GPT-4.5", "GPT-4.1-mini", "o4-mini-high", "o3"]
            for item_text in specific_items:
                elements = controller.page.locator(f'div:has-text("{item_text}")')
                count = await elements.count()
                if count > 0:
                    elem = elements.first
                    tag = await elem.evaluate("el => el.tagName")
                    role = await elem.get_attribute("role")
                    print(f"    '{item_text}': found {count} times, first is <{tag} role='{role}'>")
            
            # Check if "More models" is clickable
            print("\n📋 Testing 'More models' interaction...")
            more_models = controller.page.locator('div[role="menuitem"]:has-text("More models")').first
            if await more_models.count() > 0:
                print("  Found 'More models' item")
                
                # Try hovering first
                await more_models.hover()
                await asyncio.sleep(0.5)
                print("  Hovered over 'More models'")
                
                # Now click it
                await more_models.click()
                await asyncio.sleep(1)
                print("  Clicked 'More models'")
                
                # Look for submenu items
                print("\n  Looking for submenu items...")
                # Re-check menu items after clicking
                new_menu_items = controller.page.locator('div[role="menuitem"]')
                new_count = await new_menu_items.count()
                print(f"  After click: {new_count} menu items")
                
                # Look specifically for GPT-4.1
                gpt41 = controller.page.locator('div[role="menuitem"]:has-text("GPT-4.1")').first
                if await gpt41.count() > 0:
                    print("  ✅ Found GPT-4.1 in submenu!")
                else:
                    # Try alternative selectors
                    gpt41_alt = controller.page.locator('div:has-text("GPT-4.1"):not(:has(div))').first
                    if await gpt41_alt.count() > 0:
                        print("  ✅ Found GPT-4.1 with alternative selector!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def main():
    """Run all tests"""
    print("🧪 More Models Submenu Tests")
    print("=" * 50)
    
    # Test 1: Debug menu structure
    await debug_model_picker_structure()
    
    # Test 2: Test model selection
    await test_more_models_improved()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())