"""
Quota tracking for ChatGPT limited modes
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class QuotaTracker:
    """Track usage of limited ChatGPT modes to avoid exceeding quotas"""
    
    QUOTAS = {
        "deep_research": {
            "limit": 250,
            "period": "month",
            "warning_threshold": 0.8  # Warn at 80% usage
        },
        "agent_mode": {
            "limit": 400,
            "period": "month", 
            "warning_threshold": 0.9  # Warn at 90% usage
        }
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize quota tracker with optional data directory"""
        if data_dir is None:
            data_dir = Path.home() / ".chatgpt-automation-mcp"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.quota_file = self.data_dir / "quota_usage.json"
        self.usage_data = self._load_usage()
    
    def _load_usage(self) -> Dict:
        """Load usage data from file"""
        if self.quota_file.exists():
            try:
                with open(self.quota_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load quota usage: {e}")
        
        return {
            "deep_research": {"count": 0, "last_reset": self._current_month()},
            "agent_mode": {"count": 0, "last_reset": self._current_month()}
        }
    
    def _save_usage(self):
        """Save usage data to file"""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quota usage: {e}")
    
    def _current_month(self) -> str:
        """Get current month as YYYY-MM string"""
        return datetime.now(timezone.utc).strftime("%Y-%m")
    
    def _reset_if_new_month(self, mode: str):
        """Reset count if we're in a new month"""
        current_month = self._current_month()
        if self.usage_data[mode]["last_reset"] != current_month:
            logger.info(f"New month detected, resetting {mode} quota")
            self.usage_data[mode] = {
                "count": 0,
                "last_reset": current_month
            }
            self._save_usage()
    
    def check_quota(self, mode: str) -> tuple[bool, str]:
        """
        Check if quota allows using this mode
        
        Returns:
            tuple: (allowed: bool, message: str)
        """
        if mode not in self.QUOTAS:
            return True, ""
        
        self._reset_if_new_month(mode)
        
        current_usage = self.usage_data[mode]["count"]
        limit = self.QUOTAS[mode]["limit"]
        warning_threshold = self.QUOTAS[mode]["warning_threshold"]
        
        if current_usage >= limit:
            return False, f"Monthly quota exceeded for {mode}: {current_usage}/{limit} used"
        
        usage_ratio = current_usage / limit
        if usage_ratio >= warning_threshold:
            percentage = int(usage_ratio * 100)
            return True, f"Warning: {mode} quota at {percentage}% ({current_usage}/{limit})"
        
        return True, f"{mode} usage: {current_usage}/{limit}"
    
    def increment_usage(self, mode: str):
        """Increment usage count for a mode"""
        if mode not in self.QUOTAS:
            return
        
        self._reset_if_new_month(mode)
        self.usage_data[mode]["count"] += 1
        self._save_usage()
        
        # Log current usage
        current = self.usage_data[mode]["count"]
        limit = self.QUOTAS[mode]["limit"]
        logger.info(f"{mode} usage incremented: {current}/{limit}")
    
    def get_usage_summary(self) -> Dict:
        """Get current usage summary for all tracked modes"""
        summary = {}
        
        for mode, quota_info in self.QUOTAS.items():
            self._reset_if_new_month(mode)
            current = self.usage_data[mode]["count"]
            limit = quota_info["limit"]
            percentage = int((current / limit) * 100)
            
            summary[mode] = {
                "current": current,
                "limit": limit,
                "percentage": percentage,
                "remaining": limit - current
            }
        
        return summary
    
    def should_warn_user(self, mode: str) -> bool:
        """Check if we should warn the user about quota usage"""
        if mode not in self.QUOTAS:
            return False
        
        self._reset_if_new_month(mode)
        
        current = self.usage_data[mode]["count"]
        limit = self.QUOTAS[mode]["limit"]
        warning_threshold = self.QUOTAS[mode]["warning_threshold"]
        
        return (current / limit) >= warning_threshold