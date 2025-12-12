"""Function tools for LLM to control interview stage transitions."""
from livekit.agents.llm import function_tool


@function_tool()
async def transition_to_past_experience() -> str:
    """
    Call this function when the candidate has completed their self-introduction
    and you're ready to move to discussing their past work experiences.
    
    Use this when:
    - The candidate has finished introducing themselves
    - They've paused after completing their introduction
    - They've indicated they're done (e.g., "that's about it", "that's me")
    
    Returns:
        A confirmation string indicating the transition
    """
    return "transitioning_to_past_experience"


@function_tool()
async def complete_interview() -> str:
    """
    Call this function when the interview discussion is complete and you want to close the session.
    
    Use this when:
    - You've discussed the candidate's past experiences adequately
    - The candidate has finished sharing their experiences
    - You're ready to wrap up and thank them
    
    Returns:
        A confirmation string indicating interview completion
    """
    return "interview_complete"


@function_tool()
async def request_more_details(topic: str) -> str:
    """
    Request more details about a specific topic the candidate mentioned.
    
    Args:
        topic: The topic or aspect you'd like more information about
        
    Returns:
        A confirmation string
    """
    return f"requesting_more_details_about_{topic}"

