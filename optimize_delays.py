#!/usr/bin/env python3
"""
Script to replace hardcoded animation delays with configurable ones
"""

import re
from pathlib import Path


def replace_delays_in_file(file_path: Path):
    """Replace hardcoded delays in a single file"""
    
    content = file_path.read_text()
    original_content = content
    
    # Define replacement patterns
    replacements = [
        # Menu and interaction delays
        (r'await asyncio\.sleep\(0\.3\)', 'await asyncio.sleep(get_delay("hover_delay"))'),
        (r'await asyncio\.sleep\(1\.0\)\s*#.*submenu animation', 'await asyncio.sleep(get_delay("more_models_menu"))  # Wait for submenu animation'),
        (r'await asyncio\.sleep\(0\.2\)', 'await asyncio.sleep(get_delay("hover_quick"))'),
        (r'await asyncio\.sleep\(1\.5\)\s*#.*selection to apply', 'await asyncio.sleep(get_delay("model_selection"))  # Increased wait for selection to apply'),
        (r'await asyncio\.sleep\(1\.0\)\s*#.*animation', 'await asyncio.sleep(get_delay("sidebar_animation"))  # Wait for animation'),
        (r'await asyncio\.sleep\(0\.5\)\s*#.*menu', 'await asyncio.sleep(get_delay("menu_open"))  # Wait for menu'),
        (r'await asyncio\.sleep\(1\)\s*#.*UI time to update', 'await asyncio.sleep(get_delay("toggle_verify"))  # Give UI time to update'),
        (r'await asyncio\.sleep\(1\.0\)(?!\s*#)', 'await asyncio.sleep(get_delay("ui_update"))'),
        (r'await asyncio\.sleep\(0\.5\)(?!\s*#)', 'await asyncio.sleep(get_delay("click_delay"))'),
        (r'await asyncio\.sleep\(1\)(?!\s*#)', 'await asyncio.sleep(get_delay("ui_update"))'),
    ]
    
    # Apply replacements
    changes_made = 0
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made += len(re.findall(pattern, content))
            content = new_content
    
    if content != original_content:
        # Check if we need to add import
        if 'from .animation_config import get_delay' not in content and 'get_delay(' in content:
            # Find the imports section and add our import
            imports_match = re.search(r'(from playwright\.async_api import[^)]*\))', content)
            if imports_match:
                import_end = imports_match.end()
                content = content[:import_end] + '\n\nfrom .animation_config import get_delay' + content[import_end:]
        
        file_path.write_text(content)
        print(f"✅ Updated {file_path.name}: {changes_made} delays replaced")
        return changes_made
    else:
        print(f"⚪ {file_path.name}: No changes needed")
        return 0


def main():
    """Replace delays in all relevant files"""
    
    # Files to process
    src_dir = Path("src/chatgpt_automation_mcp")
    files_to_process = [
        src_dir / "browser_controller.py",
        src_dir / "error_recovery.py",
    ]
    
    # Also process test files
    test_dir = Path("tests")
    test_files = list(test_dir.glob("test_*.py"))
    
    total_changes = 0
    
    print("🔧 Optimizing animation delays...")
    print("=" * 50)
    
    # Process source files
    print("\n📁 Source files:")
    for file_path in files_to_process:
        if file_path.exists():
            total_changes += replace_delays_in_file(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    # Process test files
    print("\n📁 Test files:")
    for file_path in test_files:
        if file_path.exists():
            total_changes += replace_delays_in_file(file_path)
    
    print("\n" + "=" * 50)
    print(f"🎉 Total changes made: {total_changes}")
    
    if total_changes > 0:
        print("\n📝 Next steps:")
        print("1. Test the changes with: uv run run-tests --auto-enable")
        print("2. Run integration tests to verify browser automation still works")
        print("3. Adjust animation_config.py timings if needed")
        print("4. Set CHATGPT_ANIMATION_SPEED=0.5 for faster testing")


if __name__ == "__main__":
    main()