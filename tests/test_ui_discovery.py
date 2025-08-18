#!/usr/bin/env python3
"""
UI Discovery Tests for ChatGPT Automation MCP
Maps all interactive elements and finds location of broken features
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Test will be marked as requiring browser
pytestmark = [pytest.mark.browser, pytest.mark.ui_dependent]


@pytest.mark.asyncio
async def test_discover_all_ui_elements(browser):
    """
    Use browser to map ALL interactive elements.
    This test documents the current UI state.
    """
    browser.test_name = "ui_discovery"
    
    # Navigate to ChatGPT
    await browser.controller.page.goto("https://chatgpt.com")
    await browser.wait_for_stable_ui()
    
    # Take initial screenshot
    await browser.screenshot("01_main_interface")
    
    # Document all major UI areas
    ui_map = {
        "timestamp": datetime.now().isoformat(),
        "url": browser.controller.page.url,
        "elements": {}
    }
    
    # 1. Check input area buttons
    print("\n=== Input Area Buttons ===")
    input_buttons = await browser.controller.page.locator('button.composer-btn, .composer-btn').all()
    print(f"Found {len(input_buttons)} composer buttons")
    
    for i, button in enumerate(input_buttons):
        try:
            aria_label = await button.get_attribute("aria-label")
            title = await button.get_attribute("title")
            text = await button.inner_text()
            print(f"  Button {i}: aria-label='{aria_label}', title='{title}', text='{text}'")
            
            ui_map["elements"][f"composer_btn_{i}"] = {
                "aria_label": aria_label,
                "title": title,
                "text": text
            }
        except Exception as e:
            print(f"  Button {i}: Error reading attributes - {e}")
    
    # 2. Click attachment/paperclip button to open menu
    print("\n=== Attachment Menu Discovery ===")
    
    # Try various selectors for the attachment button
    attachment_selectors = [
        '.composer-btn:not([aria-label*="Dictate"])',
        '.composer-btn:not([aria-label*="voice"])',
        'button[aria-label="Attach files"]',
        'button:has(svg.icon-paperclip)',
        'button.composer-btn:first-of-type',
    ]
    
    attachment_button = None
    for selector in attachment_selectors:
        button = browser.controller.page.locator(selector).first
        if await button.count() > 0 and await button.is_visible():
            attachment_button = button
            print(f"Found attachment button with selector: {selector}")
            break
    
    if attachment_button:
        await browser.screenshot("02_before_attachment_click")
        await attachment_button.click()
        await asyncio.sleep(1.0)  # Wait for menu animation
        await browser.screenshot("03_attachment_menu_open")
        
        # Find all menu items
        menu_items = await browser.controller.page.locator('div[role="menuitem"], button[role="menuitem"], div[role="option"]').all()
        print(f"Found {len(menu_items)} menu items")
        
        ui_map["elements"]["attachment_menu_items"] = []
        for i, item in enumerate(menu_items):
            try:
                text = await item.inner_text()
                role = await item.get_attribute("role")
                print(f"  Menu item {i}: '{text}' (role={role})")
                ui_map["elements"]["attachment_menu_items"].append({
                    "index": i,
                    "text": text,
                    "role": role
                })
            except Exception as e:
                print(f"  Menu item {i}: Error - {e}")
        
        # Close menu
        await browser.controller.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    else:
        print("WARNING: Could not find attachment button!")
    
    # 3. Check model selector
    print("\n=== Model Selector Discovery ===")
    await browser.screenshot("04_checking_model_selector")
    
    # Get current model display
    model_display = browser.controller.page.locator('[data-testid="model-switcher-dropdown-button"], button:has-text("ChatGPT")').first
    if await model_display.count() > 0:
        try:
            model_text = await model_display.inner_text()
            print(f"Current model display: '{model_text}'")
            ui_map["elements"]["current_model"] = model_text
            
            # Try to click to open model menu (may not be visible)
            if await model_display.is_visible():
                await model_display.click()
                await asyncio.sleep(1.0)
                await browser.screenshot("05_model_menu_open")
                
                # Close menu
                await browser.controller.page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
            else:
                print("Model selector found but not visible/clickable")
        except Exception as e:
            print(f"Error accessing model selector: {e}")
    
    # 4. Look for Think Longer and Deep Research in various locations
    print("\n=== Searching for Think Longer and Deep Research ===")
    
    # Search patterns
    search_patterns = [
        ('Think longer', 'think_longer'),
        ('Think Longer', 'think_longer_caps'),
        ('Deep research', 'deep_research'),
        ('Deep Research', 'deep_research_caps'),
        ('Extended thinking', 'extended_thinking'),
        ('Research mode', 'research_mode'),
    ]
    
    for pattern, key in search_patterns:
        elements = await browser.controller.page.locator(f'text="{pattern}"').all()
        if elements:
            print(f"Found '{pattern}': {len(elements)} occurrences")
            ui_map["elements"][key] = len(elements)
            for i, elem in enumerate(elements):
                try:
                    parent = await elem.locator('..').first
                    parent_tag = await parent.evaluate('el => el.tagName')
                    parent_role = await parent.get_attribute('role')
                    print(f"  Occurrence {i}: parent tag={parent_tag}, role={parent_role}")
                except Exception:
                    pass
    
    # 5. Save UI map to file
    ui_map_path = Path(__file__).parent / "test_data" / "ui_map.json"
    ui_map_path.parent.mkdir(exist_ok=True)
    
    with open(ui_map_path, 'w') as f:
        json.dump(ui_map, f, indent=2)
    
    print(f"\n=== UI Map saved to: {ui_map_path} ===")
    
    # Final screenshot
    await browser.screenshot("06_discovery_complete")
    
    # Assert we found some elements
    assert len(ui_map["elements"]) > 0, "Should discover UI elements"
    
    # Report findings (don't fail - this is discovery)
    print("\n=== DISCOVERY RESULTS ===")
    if "think_longer" not in ui_map["elements"] and "think_longer_caps" not in ui_map["elements"]:
        print("❌ Think Longer option NOT FOUND in UI - needs investigation")
    else:
        print("✅ Think Longer option FOUND")
    
    if "deep_research" not in ui_map["elements"] and "deep_research_caps" not in ui_map["elements"]:
        print("❌ Deep Research option NOT FOUND in UI - needs investigation")
    else:
        print("✅ Deep Research option FOUND")


@pytest.mark.asyncio
async def test_find_think_longer_location(browser):
    """
    TDD: Find where Think Longer mode is in the current UI.
    This test SHOULD FAIL initially, then we fix it.
    """
    browser.test_name = "find_think_longer"
    
    # Navigate with a model that supports Think Longer
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-thinking")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_gpt5_thinking_loaded")
    
    print("\n=== Searching for Think Longer Option ===")
    
    # Strategy 1: Check attachment menu
    attachment_button = browser.controller.page.locator('.composer-btn:not([aria-label*="Dictate"])').first
    if await attachment_button.count() > 0:
        await attachment_button.click()
        await asyncio.sleep(1.0)
        await browser.screenshot("02_attachment_menu")
        
        # Look for Think Longer
        think_longer = await browser.controller.page.locator('text=/think.*longer/i').count()
        print(f"Think Longer in attachment menu: {think_longer > 0}")
        
        await browser.controller.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    
    # Strategy 2: Check for a toggle or button near input
    think_toggle = await browser.controller.page.locator('button:has-text("Think"), label:has-text("Think")').count()
    print(f"Think toggle/button near input: {think_toggle > 0}")
    
    # Strategy 3: Check model-specific UI changes
    await browser.screenshot("03_checking_ui_state")
    
    # Look for any UI element mentioning thinking
    thinking_elements = await browser.controller.page.locator('text=/think/i').all()
    print(f"Found {len(thinking_elements)} elements mentioning 'think'")
    
    for i, elem in enumerate(thinking_elements):
        text = await elem.inner_text()
        print(f"  Element {i}: '{text}'")
    
    # This assertion will likely fail initially - that's expected in TDD
    assert think_longer > 0 or think_toggle > 0 or len(thinking_elements) > 0, \
        "Think Longer option should exist somewhere in the UI"


@pytest.mark.asyncio
async def test_find_deep_research_location(browser):
    """
    TDD: Find where Deep Research mode is in the current UI.
    This test SHOULD FAIL initially, then we fix it.
    """
    browser.test_name = "find_deep_research"
    
    # Navigate with a model that supports Deep Research
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-pro")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_gpt5_pro_loaded")
    
    print("\n=== Searching for Deep Research Option ===")
    
    # Strategy 1: Check attachment menu
    attachment_button = browser.controller.page.locator('.composer-btn:not([aria-label*="Dictate"])').first
    if await attachment_button.count() > 0:
        await attachment_button.click()
        await asyncio.sleep(1.0)
        await browser.screenshot("02_attachment_menu")
        
        # Look for Deep Research
        deep_research = await browser.controller.page.locator('text=/deep.*research/i').count()
        print(f"Deep Research in attachment menu: {deep_research > 0}")
        
        # Also check for just "Research"
        research = await browser.controller.page.locator('text="Research"').count()
        print(f"'Research' in attachment menu: {research > 0}")
        
        await browser.controller.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    
    # Strategy 2: Check for research-related buttons
    research_buttons = await browser.controller.page.locator('button:has-text("Research"), button:has-text("Deep")').all()
    print(f"Found {len(research_buttons)} research-related buttons")
    
    for i, btn in enumerate(research_buttons):
        text = await btn.inner_text()
        print(f"  Button {i}: '{text}'")
    
    # Strategy 3: Check if it appears after sending a research query
    await browser.controller.page.fill('textarea[placeholder*="Message"]', "Research the latest developments in quantum computing")
    await browser.screenshot("03_research_query_typed")
    
    # Check if any research options appeared
    await asyncio.sleep(1.0)
    research_ui = await browser.controller.page.locator('text=/research/i').all()
    print(f"Research UI elements after typing query: {len(research_ui)}")
    
    # This assertion will likely fail initially - that's expected in TDD
    assert deep_research > 0 or research > 0 or len(research_buttons) > 0, \
        "Deep Research option should exist (users pay for this feature!)"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_ui_discovery.py -v -s
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))