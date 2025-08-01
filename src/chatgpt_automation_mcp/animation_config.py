"""
Animation and timing configuration for ChatGPT MCP.

This module provides configurable timing constants to replace hardcoded delays
throughout the codebase, enabling better performance tuning and testing.
"""

import os
from typing import Dict, Any


class AnimationConfig:
    """Configuration for animation delays and UI timing"""
    
    def __init__(self):
        # Environment-based multiplier for all delays (useful for testing/debugging)
        self._speed_multiplier = float(os.getenv("CHATGPT_ANIMATION_SPEED", "1.0"))
        
        # Base timing constants (in seconds)
        self._base_timings = {
            # Browser startup and connection
            "browser_startup": 5.0,          # Chrome startup with debugging
            "browser_close": 2.0,            # Time to close Chrome gracefully
            "browser_ready": 3.0,            # Wait for Chrome to be ready
            
            # UI interaction delays
            "click_delay": 0.5,              # General click animation delay
            "menu_open": 0.5,                # Menu opening animation
            "menu_close": 0.5,               # Menu closing animation
            "hover_delay": 0.3,              # Hover effect delay
            "hover_quick": 0.2,              # Quick hover for tooltips
            
            # Model selection delays
            "model_picker_open": 0.5,        # Model picker animation
            "model_selection": 1.5,          # Model selection confirmation
            "model_verify": 0.5,             # Verify model change
            "more_models_menu": 1.0,         # "More models" submenu animation
            
            # UI state changes
            "sidebar_animation": 1.0,        # Sidebar open/close
            "toggle_animation": 1.0,         # Web search, Deep Research toggle
            "toggle_verify": 1.0,            # Verify toggle state
            "ui_update": 1.0,                # General UI update wait
            
            # File operations
            "file_upload": 1.0,              # File upload processing
            
            # Error recovery delays
            "recovery_wait": 2.0,            # General recovery wait
            "page_load": 3.0,                # Page reload wait
            "network_stabilize": 2.0,        # Network error recovery
            "timeout_recovery": 3.0,         # Timeout error recovery
            
            # Test-specific delays (shorter for speed)
            "test_page_load": 3.0,           # Test page loading
            "test_action": 2.0,              # Test action delays
            "test_quick": 1.0,               # Quick test operations
            "test_verify": 0.5,              # Test verification
        }
    
    def get(self, timing_key: str) -> float:
        """Get a timing value with speed multiplier applied"""
        base_time = self._base_timings.get(timing_key, 1.0)
        return base_time * self._speed_multiplier
    
    def set_speed_multiplier(self, multiplier: float):
        """Set global speed multiplier (useful for testing)"""
        self._speed_multiplier = max(0.1, multiplier)  # Minimum 0.1x speed
    
    def get_all_timings(self) -> Dict[str, float]:
        """Get all timing values with multiplier applied"""
        return {key: self.get(key) for key in self._base_timings.keys()}
    
    def update_timing(self, key: str, value: float):
        """Update a specific timing value"""
        self._base_timings[key] = value


# Global instance
animation_config = AnimationConfig()


# Convenience functions for common usage patterns
def get_delay(timing_key: str) -> float:
    """Get a delay value"""
    return animation_config.get(timing_key)


def quick_delay() -> float:
    """Quick delay for minor UI updates (0.5s base)"""
    return animation_config.get("click_delay")


def menu_delay() -> float:
    """Menu animation delay (0.5s base)"""
    return animation_config.get("menu_open")


def ui_delay() -> float:
    """General UI update delay (1.0s base)"""
    return animation_config.get("ui_update")


def browser_delay() -> float:
    """Browser operation delay (3.0s base)"""
    return animation_config.get("browser_ready")


# Environment-based shortcuts
def is_fast_mode() -> bool:
    """Check if we're in fast mode (speed multiplier < 1.0)"""
    return animation_config._speed_multiplier < 1.0


def is_debug_mode() -> bool:
    """Check if we're in debug mode (speed multiplier > 1.0)"""
    return animation_config._speed_multiplier > 1.0


# Test utilities
def set_test_mode(enabled: bool = True):
    """Enable/disable test mode with faster timings"""
    if enabled:
        animation_config.set_speed_multiplier(0.5)  # 2x faster
    else:
        animation_config.set_speed_multiplier(1.0)  # Normal speed


def set_debug_mode(enabled: bool = True):
    """Enable/disable debug mode with slower timings"""
    if enabled:
        animation_config.set_speed_multiplier(2.0)  # 2x slower for debugging
    else:
        animation_config.set_speed_multiplier(1.0)  # Normal speed