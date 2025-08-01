#!/usr/bin/env python3
"""
Debug the Tools menu to understand its structure
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def debug_tools_menu():
    """Debug Tools menu structure"""
    controller = ChatGPTBrowserController()
    
    try:
        print("🚀 Debugging Tools menu...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Try to open Tools menu
        print("\n📋 Looking for Tools button...")
        
        # Check what buttons we can find
        button_selectors = [
            'button[aria-label="Choose tool"]',
            '#system-hint-button',
            'button.composer-btn',
            'button[data-state="open"]',
            'button:has-text("Tools")',
        ]
        
        for selector in button_selectors:
            count = await controller.page.locator(selector).count()
            if count > 0:
                text = await controller.page.locator(selector).first.text_content()
                label = await controller.page.locator(selector).first.get_attribute('aria-label')
                print(f"  Found: {selector} - Count: {count}, Text: '{text}', Label: '{label}'")
        
        # Try to click the tools button
        tools_button = controller.page.locator('button[aria-label="Choose tool"]').first
        if await tools_button.count() == 0:
            tools_button = controller.page.locator('#system-hint-button').first
            
        if await tools_button.count() > 0:
            print("\n🔧 Clicking Tools button...")
            await tools_button.click(force=True)
            await asyncio.sleep(1)
            
            # Look for menu items
            print("\n📋 Looking for menu items...")
            menu_selectors = [
                'div[role="menuitem"]',
                'button[role="menuitem"]',
                '[data-radix-menu-item]',
                'div[role="menu"] div',
                'div[role="menu"] button',
            ]
            
            for selector in menu_selectors:
                items = controller.page.locator(selector)
                count = await items.count()
                if count > 0:
                    print(f"\n  {selector}: {count} items")
                    for i in range(min(count, 10)):  # Show first 10
                        item = items.nth(i)
                        text = await item.text_content()
                        if text and text.strip():
                            print(f"    - '{text.strip()}'")
            
            # Also check for any text containing "Deep" or "Web"
            print("\n🔍 Looking for specific options...")
            deep_items = controller.page.locator('*:has-text("Deep")')
            web_items = controller.page.locator('*:has-text("Web")')
            
            deep_count = await deep_items.count()
            web_count = await web_items.count()
            
            print(f"  Elements with 'Deep': {deep_count}")
            print(f"  Elements with 'Web': {web_count}")
            
        else:
            print("❌ Tools button not found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


if __name__ == "__main__":
    asyncio.run(debug_tools_menu())