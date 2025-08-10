"""
Helper functions for determining appropriate timeouts based on model and mode
"""

def get_default_timeout(model: str = None, mode: str = None, operation: str = "response") -> int:
    """
    Get appropriate timeout based on model, mode, and operation type
    
    Args:
        model: The model name (e.g., "gpt-5", "gpt-5-thinking", "gpt-5-pro")
        mode: The mode (e.g., "deep_research", "web_search")
        operation: The operation type (e.g., "response", "thinking")
    
    Returns:
        Timeout in seconds
    """
    # Deep Research mode: Real data shows up to 6 hours worst case
    if mode and "deep_research" in mode.lower():
        return 21600  # 6 hours (users report 2-6 hour waits, we need to cover worst case!)
    
    # Model-specific timeouts
    if model:
        model_lower = model.lower()
        
        # GPT-5 family
        if "gpt-5-pro" in model_lower or "gpt 5 pro" in model_lower:
            return 1800  # 30 minutes (Pro models need extensive time)
        elif "gpt-5-thinking" in model_lower or "gpt 5 thinking" in model_lower:
            return 900  # 15 minutes (Thinking models need time for reasoning)
        elif "gpt-5" in model_lower or "gpt 5" in model_lower or model_lower == "5":
            return 300  # 5 minutes (Standard model, good balance)
        
        # o-series reasoning models
        elif "o3-pro" in model_lower or "o3 pro" in model_lower:
            return 900  # 15 minutes (Legacy reasoning expert)
        elif "o3" in model_lower:
            return 600  # 10 minutes (Advanced reasoning)
        elif "o4-mini" in model_lower or "o4 mini" in model_lower:
            return 60  # 1 minute (Fastest reasoning model)
        
        # GPT-4 family
        elif "gpt-4.5" in model_lower or "gpt 4.5" in model_lower:
            return 180  # 3 minutes (Writing and exploration)
        elif "gpt-4.1-mini" in model_lower or "gpt 4.1 mini" in model_lower:
            return 60  # 1 minute (Fastest everyday tasks)
        elif "gpt-4.1" in model_lower or "gpt 4.1" in model_lower:
            return 90  # 1.5 minutes (Quick coding and analysis)
        elif "gpt-4o" in model_lower or "4o" in model_lower:
            return 120  # 2 minutes (Legacy model)
    
    # Default timeout for unknown models
    return 120  # 2 minutes (conservative default)


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