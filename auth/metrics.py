"""Token refresh metrics tracking."""
import time
import logging
from collections import deque
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("SecureShare")


@dataclass
class RefreshEvent:
    """Represents a token refresh event."""
    timestamp: float
    success: bool
    duration_ms: float
    error_type: Optional[str]
    attempt: int


class TokenRefreshMetrics:
    """Tracks token refresh metrics for monitoring and analysis."""
    
    def __init__(self, max_events: int = 1000):
        """
        Initialize metrics tracker.
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self._events: deque = deque(maxlen=max_events)
        self._lock = None
        try:
            import threading
            self._lock = threading.Lock()
        except ImportError:
            pass
    
    def record_refresh(
        self,
        success: bool,
        duration_ms: float,
        error_type: Optional[str] = None,
        attempt: int = 1
    ) -> None:
        """
        Record a token refresh event.
        
        Args:
            success: Whether refresh was successful
            duration_ms: Duration in milliseconds
            error_type: Type of error if failed
            attempt: Attempt number (1-based)
        """
        event = RefreshEvent(
            timestamp=time.time(),
            success=success,
            duration_ms=duration_ms,
            error_type=error_type,
            attempt=attempt
        )
        
        if self._lock:
            with self._lock:
                self._events.append(event)
        else:
            self._events.append(event)
    
    def get_stats(self, window_seconds: int = 3600) -> Dict:
        """
        Get refresh statistics for a time window.
        
        Args:
            window_seconds: Time window in seconds (default 1 hour)
            
        Returns:
            Dictionary with statistics
        """
        now = time.time()
        cutoff = now - window_seconds
        
        if self._lock:
            with self._lock:
                recent_events = [e for e in self._events if e.timestamp >= cutoff]
        else:
            recent_events = [e for e in self._events if e.timestamp >= cutoff]
        
        if not recent_events:
            return {
                'total_refreshes': 0,
                'successful_refreshes': 0,
                'failed_refreshes': 0,
                'success_rate': 0.0,
                'avg_duration_ms': 0.0,
                'error_types': {},
                'avg_attempts': 0.0
            }
        
        successful = [e for e in recent_events if e.success]
        failed = [e for e in recent_events if not e.success]
        
        error_types = {}
        for event in failed:
            error_type = event.error_type or 'Unknown'
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        avg_duration = sum(e.duration_ms for e in recent_events) / len(recent_events)
        avg_attempts = sum(e.attempt for e in recent_events) / len(recent_events)
        
        return {
            'total_refreshes': len(recent_events),
            'successful_refreshes': len(successful),
            'failed_refreshes': len(failed),
            'success_rate': len(successful) / len(recent_events) if recent_events else 0.0,
            'avg_duration_ms': avg_duration,
            'error_types': error_types,
            'avg_attempts': avg_attempts,
            'window_seconds': window_seconds
        }
    
    def clear(self) -> None:
        """Clear all metrics."""
        if self._lock:
            with self._lock:
                self._events.clear()
        else:
            self._events.clear()

