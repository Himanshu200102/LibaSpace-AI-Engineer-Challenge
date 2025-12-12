"""Structured logging utilities for the interview agent."""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime


class StructuredLogger:
    """Structured logger that outputs JSON-formatted logs."""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            logger: Optional existing logger instance
        """
        self.logger = logger or logging.getLogger(name)
        self.session_id: Optional[str] = None
        
    def set_session_id(self, session_id: str):
        """Set session ID for all subsequent logs."""
        self.session_id = session_id
    
    def _log(self, level: int, event: str, **kwargs):
        """
        Log structured event.
        
        Args:
            level: Logging level
            event: Event name/type
            **kwargs: Additional context data
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "session_id": self.session_id,
            **kwargs
        }
        
        # Output as JSON for structured logging
        message = json.dumps(log_data, default=str)
        self.logger.log(level, message)
    
    def info(self, event: str, **kwargs):
        """Log info level event."""
        self._log(logging.INFO, event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        """Log warning level event."""
        self._log(logging.WARNING, event, **kwargs)
    
    def error(self, event: str, **kwargs):
        """Log error level event."""
        self._log(logging.ERROR, event, **kwargs)
    
    def debug(self, event: str, **kwargs):
        """Log debug level event."""
        self._log(logging.DEBUG, event, **kwargs)
    
    def stage_transition(self, from_stage: str, to_stage: str, reason: str, 
                        time_in_stage: float, **kwargs):
        """Log stage transition event."""
        self.info(
            "stage_transition",
            from_stage=from_stage,
            to_stage=to_stage,
            reason=reason,
            time_in_stage=time_in_stage,
            **kwargs
        )
    
    def user_speech(self, message: str, stage: str, **kwargs):
        """Log user speech event."""
        self.info(
            "user_speech",
            message_preview=message[:100],
            stage=stage,
            message_length=len(message),
            **kwargs
        )
    
    def agent_speech(self, message: str, stage: str, **kwargs):
        """Log agent speech event."""
        self.info(
            "agent_speech",
            message_preview=message[:100],
            stage=stage,
            message_length=len(message),
            **kwargs
        )
    
    def function_call(self, function_name: str, args: Dict[str, Any], stage: str, **kwargs):
        """Log function call event."""
        self.info(
            "function_call",
            function_name=function_name,
            function_args=args,
            stage=stage,
            **kwargs
        )
    
    def timeout_triggered(self, stage: str, timeout_seconds: int, actual_time: float, **kwargs):
        """Log timeout event."""
        self.warning(
            "timeout_triggered",
            stage=stage,
            timeout_seconds=timeout_seconds,
            actual_time=actual_time,
            **kwargs
        )
    
    def error_event(self, error_type: str, error_message: str, stage: str, **kwargs):
        """Log error event."""
        self.error(
            "error_occurred",
            error_type=error_type,
            error_message=error_message,
            stage=stage,
            **kwargs
        )

