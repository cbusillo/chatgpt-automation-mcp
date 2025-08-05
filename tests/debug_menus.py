#!/usr/bin/env python3
"""
Debug the More models submenu and Deep Research
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


async def debug_more_models():
    """Debug More models submenu"""
    controller = ChatGPTBrowserController()
    
    try:
        print("🚀 Debugging More models submenu...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Start new chat
        await controller.new_chat()
        await asyncio.sleep(2)
        
        # Open model picker
        print("\n📋 Opening model picker...")
        picker_selectors = [
            '[data-testid="model-picker"]',
            'button[aria-haspopup="menu"]:has(span)',
            "button[data-state]:has(span)",
        ]
        
        picker_clicked = False
        for selector in picker_selectors:
            picker = controller.page.locator(selector).first
            if await picker.count() > 0 and await picker.is_visible():
                await picker.click()
                await asyncio.sleep(1)
                picker_clicked = True
                print(f"  ✅ Clicked picker: {selector}")
                break
        
        if not picker_clicked:
            print("  ❌ Could not open model picker")
            return
        
        # Look for menu structure
        print("\n📋 Looking for menu items...")
        menu_items = controller.page.locator('div[role="menuitem"]')
        count = await menu_items.count()
        print(f"  Found {count} menu items")
        
        for i in range(count):
            item = menu_items.nth(i)
            text = await item.text_content()
            print(f"    - '{text.strip()}'")
        
        # Look specifically for "More models"
        print("\n🔍 Looking for 'More models'...")
        more_models_selectors = [
            'div[role="menuitem"]:has-text("More models")',
            'div:has-text("More models")',
            'button:has-text("More models")',
            '*:has-text("More models")',
        ]
        
        for selector in more_models_selectors:
            elem = controller.page.locator(selector).first
            if await elem.count() > 0:
                tag = await elem.evaluate("el => el.tagName")
                role = await elem.get_attribute("role")
                classes = await elem.get_attribute("class")
                print(f"  Found with {selector}: tag={tag}, role={role}, class={classes}")
                
                # Try to click it
                try:
                    await elem.click()
                    await asyncio.sleep(1)
                    print("  ✅ Clicked 'More models'")
                    
                    # Look for submenu items
                    print("\n  📋 Looking for submenu items...")
                    submenu_items = controller.page.locator('div[role="menuitem"]')
                    new_count = await submenu_items.count()
                    print(f"    Found {new_count} items after click")
                    
                    for j in range(new_count):
                        item = submenu_items.nth(j)
                        text = await item.text_content()
                        if "4.1" in text or "4.5" in text:
                            print(f"      - '{text.strip()}' ⭐")
                        else:
                            print(f"      - '{text.strip()}'")
                    
                    break
                except Exception as e:
                    print(f"  ❌ Failed to click: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def debug_deep_research():
    """Debug Deep Research in Tools menu"""
    controller = ChatGPTBrowserController()
    
    try:
        print("\n\n🚀 Debugging Deep Research...")
        await controller.launch()
        await asyncio.sleep(3)
        
        # Open Tools menu
        print("\n📋 Opening Tools menu...")
        tools_button = controller.page.locator('button[aria-label="Choose tool"]').first
        if await tools_button.count() > 0:
            await tools_button.click(force=True)
            await asyncio.sleep(1)
            print("  ✅ Opened Tools menu")
            
            # Debug menu structure
            print("\n📋 Tools menu structure:")
            menu_divs = controller.page.locator('div[role="menu"] > div')
            count = await menu_divs.count()
            print(f"  Found {count} direct children of menu")
            
            # Look for all text content
            all_text = controller.page.locator('div[role="menu"]')
            if await all_text.count() > 0:
                full_text = await all_text.first.text_content()
                print(f"\n  Full menu text: '{full_text}'")
            
            # Try different selectors for Deep research
            print("\n🔍 Looking for Deep research with different selectors...")
            selectors = [
                'div:text-is("Deep research")',
                'div:has-text("Deep research"):not(:has(div))',  # Leaf nodes only
                'div[role="menu"] div:has-text("Deep research")',
                'span:has-text("Deep research")',
                'button:has-text("Deep research")',
            ]
            
            for selector in selectors:
                elems = controller.page.locator(selector)
                count = await elems.count()
                if count > 0:
                    print(f"\n  {selector}: found {count} elements")
                    for i in range(min(count, 3)):
                        elem = elems.nth(i)
                        tag = await elem.evaluate("el => el.tagName")
                        parent_tag = await elem.evaluate("el => el.parentElement.tagName")
                        text = await elem.text_content()
                        print(f"    - tag={tag}, parent={parent_tag}, text='{text.strip()}'")
                        
                        # Try to click the most specific one
                        if i == 0:
                            try:
                                await elem.click()
                                await asyncio.sleep(1)
                                print("    ✅ Clicked!")
                            except Exception as e:
                                print(f"    ❌ Click failed: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await controller.close()


async def main():
    """Run all debug tests"""
    # Debug More models
    await debug_more_models()
    
    # Debug Deep Research
    await debug_deep_research()


if __name__ == "__main__":
    asyncio.run(main())