"""Custom Interview Agent extending Agent class."""
import asyncio
import logging
from typing import Optional
from livekit.agents import Agent, llm
from agent.state_manager import InterviewStage, InterviewStateManager
from prompts.system_prompts import get_stage_prompt
from tools.interview_tools import (
    transition_to_past_experience,
    complete_interview,
    request_more_details
)
from config.settings import SELF_INTRO_TIMEOUT, PAST_EXPERIENCE_TIMEOUT
from utils.structured_logging import StructuredLogger

logger = logging.getLogger(__name__)


class InterviewAgent(Agent):
    """Custom agent for conducting mock interviews with stage management."""
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the interview agent.
        
        Args:
            session_id: Optional session ID for logging
        """
        self.state_manager = InterviewStateManager()
        self.timeout_task: Optional[asyncio.Task] = None
        self.timeout_seconds: Optional[int] = None
        self.session_id = session_id or "unknown"
        
        # Initialize structured logger
        self.slog = StructuredLogger(__name__, logger)
        self.slog.set_session_id(self.session_id)
        
        # Initialize Agent with greeting stage instructions
        super().__init__(
            instructions=get_stage_prompt(InterviewStage.GREETING),
            tools=[
                transition_to_past_experience,
                complete_interview,
                request_more_details
            ]
        )
        
        self.slog.info(
            "agent_initialized",
            stage=self.state_manager.current_stage.value
        )
    
    async def on_agent_started(self):
        """
        Called when the agent starts.
        Start timeout monitoring for the greeting/self-intro stage.
        """
        self.slog.info("agent_started", stage=self.state_manager.current_stage.value)
        # Start timeout monitoring for greeting stage (will transition to self-intro)
        self._start_timeout_monitoring(SELF_INTRO_TIMEOUT)
    
    async def on_user_message(self, message: str):
        """
        Called when user sends a message.
        
        Args:
            message: The user's message
        """
        # Store user response in context
        self.state_manager.add_user_response(message)
        
        # Log user speech
        self.slog.user_speech(
            message=message,
            stage=self.state_manager.current_stage.value
        )
        
        # Reset stage timer on user activity (restart timeout monitoring)
        self.state_manager.reset_stage_timer()
        self._restart_timeout_monitoring()
        
        # Check for timeout and handle transitions
        await self._check_and_handle_timeout()
        
        # Update instructions based on current stage
        await self._update_stage_instructions()
    
    async def on_agent_speech(self, message: str):
        """
        Called when agent sends a message.
        
        Args:
            message: The agent's message
        """
        # Log agent speech
        self.slog.agent_speech(
            message=message,
            stage=self.state_manager.current_stage.value
        )
        
        # Transition from greeting to self-introduction after greeting completes
        if self.state_manager.current_stage == InterviewStage.GREETING:
            success, error = self.state_manager.transition_to(
                InterviewStage.SELF_INTRODUCTION,
                reason="greeting_complete"
            )
            if success:
                self.instructions = get_stage_prompt(InterviewStage.SELF_INTRODUCTION)
                self._start_timeout_monitoring(SELF_INTRO_TIMEOUT)
                self.slog.stage_transition(
                    from_stage=InterviewStage.GREETING.value,
                    to_stage=InterviewStage.SELF_INTRODUCTION.value,
                    reason="greeting_complete",
                    time_in_stage=self.state_manager.get_time_in_stage()
                )
            else:
                self.slog.error_event(
                    error_type="transition_failed",
                    error_message=error or "Unknown error",
                    stage=self.state_manager.current_stage.value
                )
        
        # Check for timeout after agent speaks
        await self._check_and_handle_timeout()
    
    async def on_function_call(self, fnc: llm.FunctionCall):
        """
        Handle function calls from LLM.
        
        Args:
            fnc: The function call from the LLM
        """
        # Log function call
        self.slog.function_call(
            function_name=fnc.name,
            args=fnc.args or {},
            stage=self.state_manager.current_stage.value
        )
        
        if fnc.name == "transition_to_past_experience":
            await self._transition_to_past_experience()
        elif fnc.name == "complete_interview":
            await self._complete_interview()
        elif fnc.name == "request_more_details":
            # This is handled by the LLM naturally, just log it
            self.slog.debug(
                "request_more_details",
                topic=fnc.args.get('topic', 'unknown') if fnc.args else 'unknown'
            )
    
    async def _transition_to_past_experience(self):
        """Transition to past experience stage."""
        if self.state_manager.current_stage == InterviewStage.PAST_EXPERIENCE:
            return
            
        from_stage = self.state_manager.current_stage
        time_in_stage = self.state_manager.get_time_in_stage()
        
        # Validate and perform transition
        success, error = self.state_manager.transition_to(
            InterviewStage.PAST_EXPERIENCE,
            reason="function_call"
        )
        
        if success:
            # Update agent instructions with conversation context
            prompt = get_stage_prompt(InterviewStage.PAST_EXPERIENCE)
            # Add context about what was discussed in self-intro
            context_summary = self.state_manager.get_conversation_summary()
            if context_summary["conversation_context"]["self_introduction"]["background"]:
                prompt += f"\n\nNote: The candidate has already introduced themselves. Reference their introduction naturally when asking about past experiences."
            
            self.instructions = prompt
            
            # Start timeout monitoring for new stage
            self._start_timeout_monitoring(PAST_EXPERIENCE_TIMEOUT)
            
            # Log transition
            self.slog.stage_transition(
                from_stage=from_stage.value,
                to_stage=InterviewStage.PAST_EXPERIENCE.value,
                reason="function_call",
                time_in_stage=time_in_stage
            )
        else:
            self.slog.error_event(
                error_type="transition_failed",
                error_message=error or "Unknown error",
                stage=self.state_manager.current_stage.value
            )
    
    async def _complete_interview(self):
        """Complete the interview."""
        if self.state_manager.current_stage == InterviewStage.CLOSING:
            return
            
        from_stage = self.state_manager.current_stage
        time_in_stage = self.state_manager.get_time_in_stage()
        
        # Validate and perform transition
        success, error = self.state_manager.transition_to(
            InterviewStage.CLOSING,
            reason="function_call"
        )
        
        if success:
            # Update agent instructions
            self.instructions = get_stage_prompt(InterviewStage.CLOSING)
            
            # Stop timeout monitoring (no more transitions)
            self._stop_timeout_monitoring()
            
            # Log transition
            self.slog.stage_transition(
                from_stage=from_stage.value,
                to_stage=InterviewStage.CLOSING.value,
                reason="function_call",
                time_in_stage=time_in_stage
            )
            
            # Log interview completion summary
            summary = self.state_manager.get_conversation_summary()
            self.slog.info("interview_completed", **summary)
        else:
            self.slog.error_event(
                error_type="transition_failed",
                error_message=error or "Unknown error",
                stage=self.state_manager.current_stage.value
            )
    
    async def _update_stage_instructions(self):
        """Update agent instructions based on current stage."""
        current_prompt = get_stage_prompt(self.state_manager.current_stage)
        if self.instructions != current_prompt:
            self.instructions = current_prompt
            logger.debug(f"Updated instructions for stage: {self.state_manager.current_stage.value}")
    
    async def _check_and_handle_timeout(self):
        """
        Check if timeout should trigger transition.
        """
        stage = self.state_manager.current_stage
        
        # Determine timeout based on stage
        timeout_seconds = None
        if stage == InterviewStage.SELF_INTRODUCTION:
            timeout_seconds = SELF_INTRO_TIMEOUT
        elif stage == InterviewStage.PAST_EXPERIENCE:
            timeout_seconds = PAST_EXPERIENCE_TIMEOUT
        
        if timeout_seconds and self.state_manager.should_timeout(timeout_seconds):
            actual_time = self.state_manager.get_time_in_stage()
            self.slog.timeout_triggered(
                stage=stage.value,
                timeout_seconds=timeout_seconds,
                actual_time=actual_time
            )
            
            if stage == InterviewStage.SELF_INTRODUCTION:
                await self._transition_to_past_experience()
            elif stage == InterviewStage.PAST_EXPERIENCE:
                await self._complete_interview()
    
    def _start_timeout_monitoring(self, timeout_seconds: int):
        """
        Start or restart timeout monitoring with a reusable task.
        
        Args:
            timeout_seconds: Timeout duration in seconds
        """
        # Cancel existing task if running
        self._stop_timeout_monitoring()
        
        # Store timeout duration
        self.timeout_seconds = timeout_seconds
        
        # Start new monitoring task
        self.timeout_task = asyncio.create_task(
            self._monitor_timeout(timeout_seconds)
        )
    
    def _restart_timeout_monitoring(self):
        """
        Restart timeout monitoring with current timeout duration.
        """
        if self.timeout_seconds:
            self._start_timeout_monitoring(self.timeout_seconds)
    
    def _stop_timeout_monitoring(self):
        """Stop timeout monitoring task."""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
            self.timeout_task = None
    
    async def _monitor_timeout(self, timeout_seconds: int):
        """
        Background task to monitor timeout.
        
        Args:
            timeout_seconds: Timeout duration in seconds
        """
        try:
            await asyncio.sleep(timeout_seconds)
            # Check timeout again (user might have spoken, resetting the timer)
            await self._check_and_handle_timeout()
        except asyncio.CancelledError:
            self.slog.debug("timeout_monitoring_cancelled")
        except Exception as e:
            self.slog.error_event(
                error_type="timeout_monitoring_error",
                error_message=str(e),
                stage=self.state_manager.current_stage.value
            )
    
    def get_state_info(self) -> dict:
        """Get current state information for debugging."""
        return self.state_manager.get_stage_info()
    
    def on_agent_ended(self):
        """Called when agent ends. Clean up resources."""
        self._stop_timeout_monitoring()
        self.slog.info("agent_ended", stage=self.state_manager.current_stage.value)

