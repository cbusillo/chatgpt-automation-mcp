#!/usr/bin/env python3
"""
Focused discovery test for Deep Research feature
Goal: Find exactly where and how to activate Deep Research
"""

import pytest
import asyncio
from pathlib import Path

pytestmark = [pytest.mark.browser, pytest.mark.ui_dependent]


@pytest.mark.asyncio
async def test_deep_research_detailed_discovery(browser):
    """
    Deep dive into finding Deep Research feature
    """
    browser.test_name = "deep_research_discovery"
    
    # Navigate with model that supports Deep Research
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-pro")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_gpt5_pro_loaded")
    
    print("\n=== DEEP RESEARCH DISCOVERY ===")
    
    # 1. Check if Deep Research appears in the "More" menu
    print("\n1. Checking 'More' menu option...")
    attachment_button = browser.controller.page.locator('.composer-btn:not([aria-label*="Dictate"])').first
    if await attachment_button.count() > 0:
        await attachment_button.click()
        await asyncio.sleep(1.0)
        await browser.screenshot("02_attachment_menu_initial")
        
        # Find and click "More" option
        more_option = browser.controller.page.locator('div[role="menuitem"]:has-text("More")').first
        if await more_option.count() > 0:
            print("Found 'More' option, clicking...")
            await more_option.click()
            await asyncio.sleep(1.0)
            await browser.screenshot("03_more_menu_expanded")
            
            # Look for Deep Research in expanded menu
            deep_research_items = await browser.controller.page.locator('text=/deep.*research/i').all()
            print(f"Deep Research items after 'More': {len(deep_research_items)}")
            
            for i, item in enumerate(deep_research_items):
                try:
                    text = await item.inner_text()
                    is_visible = await item.is_visible()
                    print(f"  Item {i}: '{text}' (visible={is_visible})")
                    
                    # Get parent information
                    parent = item.locator('..')
                    parent_role = await parent.get_attribute('role')
                    print(f"    Parent role: {parent_role}")
                except Exception as e:
                    print(f"  Item {i}: Error - {e}")
            
            # Try to click Deep Research if found
            if len(deep_research_items) > 0:
                try:
                    await deep_research_items[0].click()
                    await asyncio.sleep(2.0)
                    await browser.screenshot("04_deep_research_activated")
                    print("✅ Successfully clicked Deep Research!")
                    
                    # Check what UI changed
                    research_ui = await browser.controller.page.locator('text=/research/i').all()
                    print(f"Research-related UI elements after activation: {len(research_ui)}")
                    
                except Exception as e:
                    print(f"❌ Could not click Deep Research: {e}")
        
        # Close menu if still open
        await browser.controller.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    
    # 2. Check if it appears with research queries
    print("\n2. Checking if Deep Research appears with research queries...")
    await browser.controller.page.fill('textarea[placeholder*="Message"]', 
                                       "Research the latest breakthroughs in quantum computing in 2025",
                                       timeout=60000)  # 60 second timeout
    await browser.screenshot("05_research_query_typed")
    await asyncio.sleep(2.0)
    
    # Check for any research-related UI changes
    research_elements = await browser.controller.page.locator('text=/research|deep|sources/i').all()
    print(f"Research-related elements after query: {len(research_elements)}")
    for i, elem in enumerate(research_elements[:5]):  # First 5 only
        try:
            text = await elem.inner_text()
            print(f"  Element {i}: '{text[:50]}...'")
        except Exception:
            pass
    
    # 3. Check tooltip/hover information
    print("\n3. Checking for quota/tooltip information...")
    quota_elements = await browser.controller.page.locator('text=/quota|left|remaining|250/i').all()
    print(f"Quota-related elements found: {len(quota_elements)}")
    
    # Final assessment
    print("\n=== ASSESSMENT ===")
    if len(deep_research_items) > 0:
        print("✅ Deep Research found in 'More' menu")
    else:
        print("❌ Deep Research NOT in attachment menu")
    
    await browser.screenshot("06_final_state")


@pytest.mark.asyncio
async def test_think_longer_detailed_discovery(browser):
    """
    Deep dive into finding Think Longer feature
    """
    browser.test_name = "think_longer_discovery"
    
    # Navigate with model that supports Think Longer
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-thinking")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_gpt5_thinking_loaded")
    
    print("\n=== THINK LONGER DISCOVERY ===")
    
    # 1. Check attachment menu and More submenu
    print("\n1. Checking attachment menu...")
    attachment_button = browser.controller.page.locator('.composer-btn:not([aria-label*="Dictate"])').first
    if await attachment_button.count() > 0:
        await attachment_button.click()
        await asyncio.sleep(1.0)
        await browser.screenshot("02_attachment_menu")
        
        # Check for More option
        more_option = browser.controller.page.locator('div[role="menuitem"]:has-text("More")').first
        if await more_option.count() > 0:
            await more_option.click()
            await asyncio.sleep(1.0)
            await browser.screenshot("03_more_menu")
            
            # Look for Think Longer
            think_elements = await browser.controller.page.locator('text=/think.*longer|extended.*thinking/i').all()
            print(f"Think Longer elements in More menu: {len(think_elements)}")
            
            for i, elem in enumerate(think_elements):
                try:
                    text = await elem.inner_text()
                    print(f"  Element {i}: '{text}'")
                except Exception:
                    pass
        
        await browser.controller.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    
    # 2. Check if it's a toggle or automatic with model
    print("\n2. Checking for automatic Think Longer with model...")
    
    # Type a complex reasoning query
    await browser.controller.page.fill('textarea[placeholder*="Message"]', 
                                       "Solve this complex problem step by step: If a train leaves...")
    await browser.screenshot("04_complex_query")
    
    # Check for any thinking-related UI
    thinking_ui = await browser.controller.page.locator('text=/think|reasoning|step.*by.*step/i').all()
    print(f"Thinking-related UI elements: {len(thinking_ui)}")
    
    # 3. Check if it's in a different location
    print("\n3. Checking other possible locations...")
    
    # Check near send button
    send_area = browser.controller.page.locator('button[data-testid*="send"], button[aria-label*="Send"]')
    if await send_area.count() > 0:
        # Look for nearby thinking options
        nearby = send_area.locator('..').locator('button, div[role="button"]')
        nearby_count = await nearby.count()
        print(f"Buttons near send area: {nearby_count}")
    
    # Final assessment
    print("\n=== ASSESSMENT ===")
    if len(think_elements) > 0:
        print("✅ Think Longer found")
    else:
        print("❌ Think Longer NOT found - may be automatic with gpt-5-thinking model")
    
    await browser.screenshot("05_final_state")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))