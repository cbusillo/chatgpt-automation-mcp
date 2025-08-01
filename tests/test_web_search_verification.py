"""
Test web search functionality with screenshot verification
"""

import asyncio
from pathlib import Path
from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def test_web_search_with_screenshots():
    """Test web search toggle with visual verification"""
    controller = ChatGPTBrowserController()
    screenshots_dir = Path("test_screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    try:
        print("🚀 Launching ChatGPT...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Take initial screenshot
        print("📸 Taking initial screenshot...")
        await controller.page.screenshot(path=str(screenshots_dir / "1_initial_state.png"))
        
        # Check if ready
        if not await controller.is_ready():
            print("❌ ChatGPT not ready")
            return False
            
        # Start new chat
        print("📝 Starting new chat...")
        await controller.new_chat()
        await asyncio.sleep(2)
        await controller.page.screenshot(path=str(screenshots_dir / "2_new_chat.png"))
        
        # Enable web search
        print("🔍 Enabling web search...")
        success = await controller.toggle_search_mode(True)
        print(f"   Toggle result: {'✅' if success else '❌'}")
        
        # Wait for UI update
        await asyncio.sleep(2)
        
        # Take screenshot after enabling
        print("📸 Taking screenshot after enabling web search...")
        await controller.page.screenshot(path=str(screenshots_dir / "3_web_search_enabled.png"))
        
        # Verify web search is enabled by checking for "Search" text
        search_button = controller.page.locator('button:has-text("Search")')
        search_visible = await search_button.count() > 0
        
        if search_visible:
            print("✅ Web search successfully enabled - 'Search' button visible")
        else:
            print("❌ Web search NOT enabled - 'Search' button not found")
            
        # Check input placeholder
        input_area = controller.page.locator('div[contenteditable="true"]')
        if await input_area.count() > 0:
            placeholder = await input_area.get_attribute("data-placeholder")
            print(f"   Input placeholder: {placeholder}")
            
        # Try searching something
        print("🔍 Testing search functionality...")
        await controller.send_message("What are the latest updates to ChatGPT in 2025?")
        await asyncio.sleep(5)
        
        # Take screenshot of search in action
        await controller.page.screenshot(path=str(screenshots_dir / "4_search_in_action.png"))
        
        # Disable web search
        print("🔍 Disabling web search...")
        success = await controller.toggle_search_mode(False)
        print(f"   Toggle result: {'✅' if success else '❌'}")
        
        await asyncio.sleep(2)
        await controller.page.screenshot(path=str(screenshots_dir / "5_web_search_disabled.png"))
        
        print(f"\n📁 Screenshots saved to: {screenshots_dir.absolute()}")
        print("Please check the screenshots to verify UI states!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # Take error screenshot
        if controller.page:
            await controller.page.screenshot(path=str(screenshots_dir / "error_state.png"))
        return False
    finally:
        await controller.close()


async def test_deep_research_with_screenshots():
    """Test Deep Research enabling with visual verification"""
    controller = ChatGPTBrowserController()
    screenshots_dir = Path("test_screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    try:
        print("\n🚀 Testing Deep Research...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Start new chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Try to enable Deep Research
        print("🔬 Attempting to enable Deep Research...")
        
        # Open Tools menu
        tools_button = controller.page.locator('button[aria-label="Choose tool"]').first
        if await tools_button.count() > 0:
            await tools_button.click()
            await asyncio.sleep(1)
            
            # Take screenshot of Tools menu
            await controller.page.screenshot(path=str(screenshots_dir / "6_tools_menu_open.png"))
            
            # Look for Deep Research option - use menuitemradio for specificity
            deep_research = controller.page.locator('div[role="menuitemradio"]:has-text("Deep research")').first
            if await deep_research.count() > 0:
                print("   Found Deep Research option")
                await deep_research.click()
                await asyncio.sleep(2)
                
                # Take screenshot after enabling
                await controller.page.screenshot(path=str(screenshots_dir / "7_deep_research_enabled.png"))
                print("✅ Deep Research option clicked")
            else:
                print("❌ Deep Research option not found in menu")
                
                # Get menu text for debugging
                menu = controller.page.locator('div[role="menu"]')
                if await menu.count() > 0:
                    menu_text = await menu.text_content()
                    print(f"   Menu contains: {menu_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await controller.close()


if __name__ == "__main__":
    print("Testing ChatGPT Web Search and Deep Research with Screenshots\n")
    
    # Run tests
    asyncio.run(test_web_search_with_screenshots())
    asyncio.run(test_deep_research_with_screenshots())