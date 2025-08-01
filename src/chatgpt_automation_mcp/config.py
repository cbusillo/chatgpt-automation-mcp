"""
Secure configuration management for ChatGPT automation
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration management with secure defaults"""

    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    TEMP_DIR = PROJECT_ROOT / "temp"

    # ChatGPT credentials (optional - browser may already be logged in)
    CHATGPT_EMAIL: str | None = os.getenv("CHATGPT_EMAIL")
    CHATGPT_PASSWORD: str | None = os.getenv("CHATGPT_PASSWORD")

    # Browser settings
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    DEFAULT_WAIT_TIMEOUT: int = int(os.getenv("DEFAULT_WAIT_TIMEOUT", "5000"))

    # Directories
    SCREENSHOT_DIR = Path(os.getenv("SCREENSHOT_DIR", str(TEMP_DIR / "screenshots")))
    EXPORT_DIR = Path(os.getenv("EXPORT_DIR", str(TEMP_DIR / "exports")))
    SESSION_DIR = Path(os.getenv("SESSION_DIR", str(TEMP_DIR / "sessions")))

    # Debug settings
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    SAVE_SCREENSHOTS_ON_ERROR: bool = (
        os.getenv("SAVE_SCREENSHOTS_ON_ERROR", "true").lower() == "true"
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")

    # Rate limiting
    REQUEST_DELAY: int = int(os.getenv("REQUEST_DELAY", "1000"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Session management
    PERSIST_SESSION: bool = os.getenv("PERSIST_SESSION", "true").lower() == "true"
    SESSION_NAME: str = os.getenv("SESSION_NAME", "default")
    
    # CDP Connection settings
    USE_CDP: bool = os.getenv("USE_CDP", "true").lower() == "true"
    CDP_URL: str = os.getenv("CDP_URL", "http://127.0.0.1:9222")
    
    # Animation delays
    ANIMATION_DELAY_MULTIPLIER: float = float(os.getenv("CHATGPT_ANIMATION_MULTIPLIER", "1.0"))
    
    @classmethod
    def get_animation_delay(cls, delay_type: str = "medium") -> float:
        """Get animation delay with multiplier applied"""
        from .timeout_helper import get_animation_delay
        return get_animation_delay(delay_type, cls.ANIMATION_DELAY_MULTIPLIER)

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        for dir_path in [cls.SCREENSHOT_DIR, cls.EXPORT_DIR, cls.SESSION_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_screenshot_path(cls, name: str) -> Path:
        """Get path for screenshot with timestamp"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return cls.SCREENSHOT_DIR / f"{name}_{timestamp}.png"

    @classmethod
    def validate(cls):
        """Validate configuration and warn about missing values"""
        warnings = []

        if not cls.CHATGPT_EMAIL:
            warnings.append("CHATGPT_EMAIL not set - assuming browser is already logged in")

        if cls.HEADLESS and cls.DEBUG_MODE:
            warnings.append(
                "Running in headless mode with debug enabled - screenshots only way to debug"
            )

        return warnings


# Ensure directories exist on import
Config.ensure_directories()
