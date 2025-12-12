"""State management for interview stages."""
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
import time


class InterviewStage(Enum):
    """Enumeration of interview stages."""
    GREETING = "greeting"
    SELF_INTRODUCTION = "self_introduction"
    PAST_EXPERIENCE = "past_experience"
    CLOSING = "closing"


# Valid transition map: from_stage -> [allowed_to_stages]
VALID_TRANSITIONS = {
    InterviewStage.GREETING: [InterviewStage.SELF_INTRODUCTION],
    InterviewStage.SELF_INTRODUCTION: [InterviewStage.PAST_EXPERIENCE],
    InterviewStage.PAST_EXPERIENCE: [InterviewStage.CLOSING],
    InterviewStage.CLOSING: []  # No transitions from closing
}


class InterviewStateManager:
    """Manages the state and transitions of the interview process."""
    
    def __init__(self):
        self.current_stage = InterviewStage.GREETING
        self.stage_start_time = time.time()
        self.stage_context: Dict[str, Any] = {}
        self.transition_history: List[Dict[str, Any]] = []
        # Conversation context: stores key information from each stage
        self.conversation_context: Dict[str, Any] = {
            "self_introduction": {
                "name": None,
                "background": [],
                "key_points": []
            },
            "past_experience": {
                "roles": [],
                "achievements": [],
                "challenges": []
            }
        }
        
    def can_transition_to(self, new_stage: InterviewStage) -> Tuple[bool, Optional[str]]:
        """
        Check if transition to new stage is valid.
        
        Args:
            new_stage: The stage to transition to
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        allowed_transitions = VALID_TRANSITIONS.get(self.current_stage, [])
        if new_stage not in allowed_transitions:
            return False, f"Cannot transition from {self.current_stage.value} to {new_stage.value}"
        return True, None
        
    def transition_to(self, new_stage: InterviewStage, reason: str = "") -> Tuple[bool, Optional[str]]:
        """
        Transition to a new stage with validation.
        
        Args:
            new_stage: The new stage to transition to
            reason: Optional reason for the transition
            
        Returns:
            Tuple of (success, error_message)
        """
        if self.current_stage == new_stage:
            return True, None
            
        # Validate transition
        is_valid, error_msg = self.can_transition_to(new_stage)
        if not is_valid:
            return False, error_msg
        
        # Save current stage context before transition
        self._save_stage_context()
        
        # Record transition
        self.transition_history.append({
            "from": self.current_stage.value,
            "to": new_stage.value,
            "reason": reason,
            "timestamp": time.time(),
            "time_in_previous_stage": self.get_time_in_stage()
        })
        
        self.current_stage = new_stage
        self.stage_start_time = time.time()
        self.stage_context = {}
        
        return True, None
    
    def _save_stage_context(self):
        """Save current stage context to conversation context."""
        if self.current_stage == InterviewStage.SELF_INTRODUCTION:
            # Extract key information from self-intro context
            if "responses" in self.stage_context:
                self.conversation_context["self_introduction"]["background"] = \
                    self.stage_context.get("responses", [])
        elif self.current_stage == InterviewStage.PAST_EXPERIENCE:
            # Extract key information from past experience context
            if "responses" in self.stage_context:
                self.conversation_context["past_experience"]["roles"] = \
                    self.stage_context.get("roles", [])
                self.conversation_context["past_experience"]["achievements"] = \
                    self.stage_context.get("achievements", [])
    
    def add_user_response(self, response: str):
        """
        Add user response to current stage context.
        
        Args:
            response: The user's response text
        """
        if "responses" not in self.stage_context:
            self.stage_context["responses"] = []
        self.stage_context["responses"].append({
            "text": response,
            "timestamp": time.time()
        })
    
    def add_key_point(self, key_point: str):
        """
        Add a key point extracted from user responses.
        
        Args:
            key_point: A key point or insight from the conversation
        """
        if "key_points" not in self.stage_context:
            self.stage_context["key_points"] = []
        self.stage_context["key_points"].append(key_point)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation so far.
        
        Returns:
            Dictionary with conversation summary
        """
        return {
            "current_stage": self.current_stage.value,
            "stages_completed": [t["from"] for t in self.transition_history],
            "conversation_context": self.conversation_context.copy(),
            "total_transitions": len(self.transition_history)
        }
    
    def get_time_in_stage(self) -> float:
        """Get time elapsed in current stage in seconds."""
        return time.time() - self.stage_start_time
        
    def should_timeout(self, timeout_seconds: int) -> bool:
        """
        Check if current stage should timeout.
        
        Args:
            timeout_seconds: Maximum time allowed in current stage
            
        Returns:
            True if timeout exceeded, False otherwise
        """
        return self.get_time_in_stage() > timeout_seconds
    
    def reset_stage_timer(self):
        """Reset the stage timer (useful when user is actively speaking)."""
        self.stage_start_time = time.time()
    
    def get_stage_info(self) -> Dict[str, Any]:
        """Get current stage information."""
        return {
            "stage": self.current_stage.value,
            "time_in_stage": self.get_time_in_stage(),
            "context": self.stage_context.copy(),
            "conversation_summary": self.get_conversation_summary()
        }

