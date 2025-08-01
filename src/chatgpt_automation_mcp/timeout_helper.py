"""
Helper functions for determining appropriate timeouts based on model and mode
"""

def get_default_timeout(model: str = None, mode: str = None, operation: str = "response") -> int:
    """
    Get appropriate timeout based on model, mode, and operation type
    
    Args:
        model: The model name (e.g., "o3-pro", "gpt-4.1")
        mode: The mode (e.g., "deep_research", "web_search")
        operation: The operation type (e.g., "response", "thinking")
    
    Returns:
        Timeout in seconds
    """
    # Deep Research mode needs extended timeout
    if mode and "deep_research" in mode.lower():
        return 1800  # 30 minutes
    
    # Model-specific timeouts
    if model:
        model_lower = model.lower()
        
        # o3-pro: Can take 20-30 minutes with queue + thinking + response
        if "o3-pro" in model_lower or "o3 pro" in model_lower:
            return 1800  # 30 minutes
        
        # o3: Can think for 5-10 minutes
        elif "o3" in model_lower and "mini" not in model_lower:
            return 600  # 10 minutes
        
        # GPT-4.1: Large context processing
        elif "gpt-4.1" in model_lower or "gpt 4.1" in model_lower:
            if "mini" in model_lower:
                return 180  # 3 minutes for mini variant
            else:
                return 300  # 5 minutes for full version
        
        # o4-mini variants: Faster but still need some time
        elif "o4-mini" in model_lower or "o4 mini" in model_lower:
            if "high" in model_lower:
                return 180  # 3 minutes for high variant
            else:
                return 120  # 2 minutes for standard
        
        # GPT-4.5: Creative tasks can take time
        elif "gpt-4.5" in model_lower or "gpt 4.5" in model_lower:
            return 180  # 3 minutes
        
        # GPT-4o: Fast multimodal
        elif "gpt-4o" in model_lower or "gpt 4o" in model_lower or "4o" in model_lower:
            return 120  # 2 minutes
    
    # Default timeout for unknown models
    return 120  # 2 minutes


def get_animation_delay(delay_type: str = "medium", multiplier: float = 1.0) -> float:
    """
    Get animation delay with optional multiplier
    
    Args:
        delay_type: "short", "medium", or "long"
        multiplier: Multiplier for the delay (e.g., 1.5 for slower systems)
    
    Returns:
        Delay in seconds
    """
    delays = {
        "short": 0.3,   # Quick transitions (hover effects)
        "medium": 0.7,  # Standard animations (menu open/close)
        "long": 1.0,    # Complex animations (submenu, page transitions)
        "extra_long": 1.5  # Model selection confirmation
    }
    
    base_delay = delays.get(delay_type, delays["medium"])
    return base_delay * multiplier


def format_timeout_for_display(seconds: int) -> str:
    """
    Format timeout value for human-readable display
    
    Args:
        seconds: Timeout in seconds
    
    Returns:
        Human-readable string (e.g., "2 minutes", "30 minutes")
    """
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hour{'s' if hours != 1 else ''}"