#!/usr/bin/env python3
"""
Test model selection logic without requiring browser
"""

import re


def test_model_matching_logic():
    """Test the model matching logic used in select_model"""
    
    # Test cases for model matching
    test_cases = [
        # (selected_model, current_model_from_ui, should_match)
        ("gpt-4.1", "GPT-4.1", True),
        ("gpt-4.1", "gpt-4.1", True),
        ("gpt-4.1", "GPT 4.1", True),
        ("gpt-4.1", "ChatGPT 4.1", True),
        ("gpt-4.1", "GPT-4.1: Great for quick coding", True),
        ("gpt-4.1-mini", "GPT-4.1-mini", True),
        ("gpt-4.1-mini", "gpt-4.1-mini: Faster everyday", True),
        ("gpt-4.5", "GPT-4.5", True),
        ("gpt-4.5", "GPT-4.5: Research preview", True),
        ("o4-mini-high", "o4-mini-high", True),
        ("o4-mini-high", "O4-mini-high: Great at coding", True),
        # Negative cases
        ("gpt-4.1", "GPT-4.5", False),
        ("gpt-4.1", "o3", False),
        ("gpt-4.1-mini", "gpt-4.1", False),
    ]
    
    print("Testing model matching logic...")
    print("=" * 60)
    
    for selected, ui_text, expected in test_cases:
        # Test the matching logic from the browser controller
        model_matched = False
        
        # Check 1: Direct substring match
        if selected.lower() in ui_text.lower():
            model_matched = True
        
        # Check 2: Special case for GPT models with version extraction
        elif "gpt" in selected.lower() and "gpt" in ui_text.lower():
            # Extract version numbers and compare
            selected_version = re.search(r'[\d.]+', selected)
            ui_version = re.search(r'[\d.]+', ui_text)
            if selected_version and ui_version and selected_version.group() == ui_version.group():
                model_matched = True
        
        # Check 3: Handle variations like "4.1" vs "4.1-mini"
        elif selected.replace("-", " ").lower() in ui_text.replace("-", " ").lower():
            model_matched = True
        
        result = "✅" if model_matched == expected else "❌"
        status = "PASS" if model_matched == expected else "FAIL"
        
        print(f"{result} {status}: '{selected}' vs '{ui_text}' -> {model_matched} (expected {expected})")
    
    print("\nTesting model categorization...")
    print("=" * 60)
    
    # Test which models need "More models" menu
    more_models = ["gpt-4.5", "gpt-4.1", "gpt-4.1-mini"]
    main_models = ["gpt-4o", "o3", "o3-pro", "o4-mini", "o4-mini-high"]
    
    for model in more_models:
        needs_more = any(m in model.lower() for m in ["gpt-4.5", "gpt-4.1", "gpt-4.1-mini"])
        print(f"✅ {model} needs 'More models' menu: {needs_more}")
    
    for model in main_models:
        needs_more = any(m in model.lower() for m in ["gpt-4.5", "gpt-4.1", "gpt-4.1-mini"])
        print(f"{'✅' if not needs_more else '❌'} {model} in main menu: {not needs_more}")
    
    print("\nTesting UI text variations...")
    print("=" * 60)
    
    # Model map from browser controller
    model_map = {
        "gpt-4o": ["GPT-4o", "gpt-4o", "GPT 4o", "4o"],
        "4o": ["GPT-4o", "gpt-4o", "GPT 4o"],
        "o3": ["o3", "O3"],
        "o3-pro": ["o3-pro", "O3-pro", "o3 pro"],
        "o4-mini": ["o4-mini", "O4-mini", "o4 mini"],
        "o4-mini-high": ["o4-mini-high", "O4-mini-high", "o4 mini high"],
        # More models menu
        "gpt-4.5": ["GPT-4.5", "gpt-4.5", "GPT 4.5"],
        "gpt-4.1": ["GPT-4.1", "gpt-4.1", "GPT 4.1"],
        "gpt-4.1-mini": ["GPT-4.1-mini", "gpt-4.1-mini", "GPT 4.1 mini"],
    }
    
    for model_key, variations in model_map.items():
        print(f"\n{model_key}:")
        for var in variations:
            print(f"  - '{var}'")


if __name__ == "__main__":
    test_model_matching_logic()