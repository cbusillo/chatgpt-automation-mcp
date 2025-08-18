#!/usr/bin/env python3
"""
TDD test to fix Think Longer and Deep Research features
This test will help us find and fix the actual locations
"""

import pytest
import asyncio
from pathlib import Path

pytestmark = [pytest.mark.browser, pytest.mark.ui_dependent]


@pytest.mark.asyncio
async def test_fix_deep_research_implementation(browser):
    """
    TDD: Fix Deep Research feature by finding its actual location
    """
    browser.test_name = "fix_deep_research"
    
    # Navigate with model that supports Deep Research
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-pro")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_gpt5_pro_loaded")
    
    print("\n=== FIXING DEEP RESEARCH IMPLEMENTATION ===")
    
    # The current implementation looks in attachment menu
    # Let's check if it's actually somewhere else
    
    # Strategy 1: Check if Deep Research is a model variant
    print("\n1. Checking if Deep Research is a model variant...")
    
    # Try navigating with research in URL
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-pro&mode=research")
    await browser.wait_for_stable_ui()
    await browser.screenshot("02_with_research_param")
    
    # Check if UI changed
    research_ui = await browser.controller.page.locator('text=/research|deep|sources/i').all()
    print(f"Research UI elements with URL param: {len(research_ui)}")
    
    # Strategy 2: Check if it's activated by typing research keywords
    print("\n2. Checking if Deep Research activates with keywords...")
    
    # Go back to clean state
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-pro")
    await browser.wait_for_stable_ui()
    
    # Find the correct textarea selector
    textarea_selectors = [
        'textarea[data-testid="composer-input"]',
        'textarea[placeholder*="Message"]',
        'textarea[placeholder*="message"]',
        'textarea#prompt-textarea',
        'div[contenteditable="true"]',
    ]
    
    textarea = None
    for selector in textarea_selectors:
        elem = browser.controller.page.locator(selector).first
        if await elem.count() > 0:
            textarea = elem
            print(f"Found textarea with selector: {selector}")
            break
    
    if textarea:
        # Type a research query
        await textarea.fill("Deep research: Latest breakthroughs in quantum computing 2025", timeout=60000)
        await browser.screenshot("03_research_query_typed")
        await asyncio.sleep(2.0)
        
        # Check if Deep Research UI appeared
        research_elements = await browser.controller.page.locator('text=/research|deep|sources/i').all()
        print(f"Research elements after typing: {len(research_elements)}")
        
        for i, elem in enumerate(research_elements[:3]):
            try:
                text = await elem.inner_text()
                print(f"  Element {i}: '{text[:50]}...'")
            except Exception:
                pass
    
    # Strategy 3: Check if it's in a different menu
    print("\n3. Checking other menus and buttons...")
    
    # Look for any buttons that might trigger research
    all_buttons = await browser.controller.page.locator('button').all()
    research_buttons = []
    for btn in all_buttons[:20]:  # Check first 20 buttons
        try:
            text = await btn.inner_text()
            if text and any(keyword in text.lower() for keyword in ['research', 'deep', 'explore']):
                research_buttons.append(btn)
                if len(research_buttons) >= 5:  # Limit to first 5
                    break
        except Exception:
            continue
    print(f"Research-related buttons found: {len(research_buttons)}")
    
    for i, btn in enumerate(research_buttons[:3]):
        try:
            text = await btn.inner_text()
            aria_label = await btn.get_attribute("aria-label")
            print(f"  Button {i}: text='{text}', aria-label='{aria_label}'")
        except Exception:
            pass
    
    # Final check: Look for Deep Research text anywhere
    deep_research_anywhere = await browser.controller.page.locator('text="Deep research"').count()
    deep_research_case_insensitive = await browser.controller.page.locator('text=/deep research/i').count()
    
    print(f"\n=== RESULTS ===")
    print(f"'Deep research' (exact): {deep_research_anywhere} occurrences")
    print(f"'deep research' (case insensitive): {deep_research_case_insensitive} occurrences")
    
    # Create the fix based on findings
    if deep_research_anywhere > 0 or deep_research_case_insensitive > 0:
        print("\n✅ Deep Research found - updating implementation...")
        # TODO: Update browser_controller.py with correct selectors
    else:
        print("\n❌ Deep Research not found - may be a Pro-only feature or renamed")
    
    await browser.screenshot("04_final_state")


@pytest.mark.asyncio 
async def test_fix_think_longer_implementation(browser):
    """
    TDD: Fix Think Longer feature by finding its actual location
    """
    browser.test_name = "fix_think_longer"
    
    # Navigate with model that supports Think Longer
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-thinking")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_gpt5_thinking_loaded")
    
    print("\n=== FIXING THINK LONGER IMPLEMENTATION ===")
    
    # Strategy 1: Check if Think Longer is automatic with gpt-5-thinking
    print("\n1. Checking if Think Longer is automatic with gpt-5-thinking...")
    
    # Look for any thinking-related UI
    thinking_ui = await browser.controller.page.locator('text=/think|reasoning|deliberate/i').all()
    print(f"Thinking-related UI elements: {len(thinking_ui)}")
    
    for i, elem in enumerate(thinking_ui[:3]):
        try:
            text = await elem.inner_text()
            print(f"  Element {i}: '{text}'")
        except Exception:
            pass
    
    # Strategy 2: Check if it appears when sending a message
    print("\n2. Checking if Think Longer appears when sending...")
    
    # Find textarea
    textarea = browser.controller.page.locator('textarea[data-testid="composer-input"], textarea#prompt-textarea, div[contenteditable="true"]').first
    if await textarea.count() > 0:
        await textarea.fill("Solve step by step: What is the optimal strategy for...", timeout=60000)
        await browser.screenshot("02_complex_query")
        
        # Look for send button
        send_button = browser.controller.page.locator('button[data-testid*="send"], button[aria-label*="Send"], button:has(svg[class*="send"])').first
        if await send_button.count() > 0:
            # Check for nearby thinking options before sending
            parent = send_button.locator('..')
            nearby_buttons = await parent.locator('button').all()
            print(f"Buttons near send: {len(nearby_buttons)}")
            
            for i, btn in enumerate(nearby_buttons[:3]):
                try:
                    text = await btn.inner_text()
                    aria = await btn.get_attribute("aria-label")
                    print(f"  Nearby button {i}: text='{text}', aria='{aria}'")
                except Exception:
                    pass
    
    # Strategy 3: Check if Think Longer is a toggle or checkbox
    print("\n3. Checking for Think Longer toggle/checkbox...")
    
    toggles = await browser.controller.page.locator('input[type="checkbox"], button[role="switch"], div[role="switch"]').all()
    print(f"Toggle/checkbox elements found: {len(toggles)}")
    
    for i, toggle in enumerate(toggles[:5]):
        try:
            # Get associated label
            label = toggle.locator('..').locator('label, span')
            if await label.count() > 0:
                text = await label.first.inner_text()
                if 'think' in text.lower():
                    print(f"  Found thinking toggle: '{text}'")
        except Exception:
            pass
    
    # Final assessment
    think_longer_found = False
    if thinking_ui:
        for e in thinking_ui:
            try:
                text = await e.inner_text()
                if 'longer' in text.lower():
                    think_longer_found = True
                    break
            except Exception:
                continue
    
    print(f"\n=== RESULTS ===")
    if think_longer_found:
        print("✅ Think Longer found - updating implementation...")
    else:
        print("❌ Think Longer not found - may be automatic with gpt-5-thinking model")
        print("   Hypothesis: Think Longer is now implicit when using gpt-5-thinking model")
    
    await browser.screenshot("03_final_state")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))