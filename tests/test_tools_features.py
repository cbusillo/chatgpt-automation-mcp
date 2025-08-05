#!/usr/bin/env python3
"""
Test Tools menu features (Web Search and Deep Research)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def test_web_search():
    """Test Web Search functionality"""
    controller = ChatGPTBrowserController()
    
    try:
        print("🔍 Testing Web Search...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Start new chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Enable Web Search
        print("  Enabling Web Search...")
        success = await controller.toggle_search_mode(True)
        print(f"  Enable Web Search: {'✅' if success else '❌'}")
        
        if success:
            # Check if UI changed - look for search-specific elements
            await asyncio.sleep(1)
            
            # The interface should now show search options
            search_buttons = await controller.page.locator('button:has-text("Search")').count()
            if search_buttons > 0:
                print("  ✅ Web Search UI is active")
            else:
                print("  ⚠️ Web Search may be active but UI not detected")
            
            # Start a new chat to exit search mode
            print("  Starting new chat to exit search mode...")
            await controller.new_chat()
            await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def test_deep_research():
    """Test Deep Research functionality"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n🔬 Testing Deep Research...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Start new chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Enable Deep Research
        print("  Enabling Deep Research...")
        success = await controller.enable_deep_research()
        print(f"  Enable Deep Research: {'✅' if success else '❌'}")
        
        if success:
            # Check if UI changed - look for research-specific elements
            await asyncio.sleep(1)
            
            # The interface should now show "What are you researching?"
            research_input = await controller.page.locator('input[placeholder*="research" i]').count()
            research_text = await controller.page.locator('text=/What are you researching/i').count()
            
            if research_input > 0 or research_text > 0:
                print("  ✅ Deep Research UI is active")
                
                # Look for the sources button that appears in research mode
                sources_button = await controller.page.locator('button:has-text("Sources")').count()
                if sources_button > 0:
                    print("  ✅ Sources button found")
            else:
                print("  ⚠️ Deep Research may be active but UI not fully detected")
            
            # Start a new chat to exit research mode
            print("  Starting new chat to exit research mode...")
            await controller.new_chat()
            await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def test_tools_menu_interaction():
    """Test opening Tools menu multiple times"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n🛠️ Testing Tools menu interaction...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Test opening tools menu
        tools_button = controller.page.locator('button[aria-label="Choose tool"]').first
        if await tools_button.count() == 0:
            tools_button = controller.page.locator('#system-hint-button').first
            
        if await tools_button.count() > 0:
            # Open menu
            print("  Opening Tools menu...")
            await tools_button.click(force=True)
            await asyncio.sleep(get_delay("menu_open"))  # Wait for menu contents
            menu_text = await controller.page.locator('div[role="menu"]').text_content()
            print(f"  Menu contains: Web search: {'✅' if 'Web search' in menu_text else '❌'}")
            print(f"  Menu contains: Deep research: {'✅' if 'Deep research' in menu_text else '❌'}")
            
            # Close menu
            await controller.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
            # Test toggling between modes
            print("\n  Testing mode switching...")
            
            # Enable Web Search
            success = await controller.toggle_search_mode(True)
            print(f"  Web Search enabled: {'✅' if success else '❌'}")
            
            if success:
                # Wait and then switch to Deep Research
                await asyncio.sleep(2)
                success = await controller.enable_deep_research()
                print(f"  Switched to Deep Research: {'✅' if success else '❌'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def main():
    """Run all tools tests"""
    print("🧪 ChatGPT Tools Features Tests")
    print("=" * 50)
    
    # Test 1: Web Search
    await test_web_search()
    
    # Test 2: Deep Research
    await test_deep_research()
    
    # Test 3: Tools menu interaction
    await test_tools_menu_interaction()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())