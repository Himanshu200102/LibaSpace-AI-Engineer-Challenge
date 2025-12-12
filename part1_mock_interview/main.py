"""Main entrypoint for the LiveKit Interview Agent."""
import asyncio
import logging
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import openai, silero, assemblyai
from agent.interview_agent import InterviewAgent
from config.settings import (
    LIVEKIT_URL,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    OPENAI_API_KEY,
    ASSEMBLYAI_API_KEY,
    LLM_MODEL,
    TTS_VOICE
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for LiveKit agent job.
    
    This function is called when a new job is assigned to the agent.
    It sets up the interview agent session and handles the interview flow.
    
    Args:
        ctx: Job context containing room and connection information
    """
    logger.info("=" * 60)
    logger.info("JOB ASSIGNED - Interview agent connecting to room...")
    logger.info(f"Job ID: {ctx.job.id}")
    # Room name will be available after connecting
    logger.info("=" * 60)
    
    try:
        # Connect to the LiveKit room
        await ctx.connect()
        logger.info(f"Connected to room: {ctx.room.name}")
        
        # Create the interview agent with session ID
        session_id = ctx.room.name or f"session_{ctx.job.id}"
        agent = InterviewAgent(session_id=session_id)
        logger.info(f"Interview agent created for session: {session_id}")
        
        # Create agent session with STT, LLM, TTS
        # Using AssemblyAI for STT, OpenAI for LLM and TTS
        # Using the new AgentSession API from livekit-agents 1.x
        from livekit.agents import AgentSession
        
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=assemblyai.STT() if ASSEMBLYAI_API_KEY else openai.STT(),
            llm=openai.LLM(model=LLM_MODEL),
            tts=openai.TTS(voice=TTS_VOICE),
        )
        
        logger.info("Interview agent session created")
        
        # Set up room event listeners to track participants and tracks
        def on_participant_connected(participant):
            logger.info(f"Participant connected: {participant.identity}")
            for pub in participant.track_publications.values():
                logger.info(f"Participant {participant.identity} track: {pub.name}, kind: {pub.kind}")
        
        def on_track_published(publication, participant):
            logger.info(f"Track published by {participant.identity}: {publication.name}, kind: {publication.kind}")
            if publication.kind == "audio":
                logger.info(f"Audio track published - agent should be able to hear user now")
        
        def on_track_subscribed(track, publication, participant):
            logger.info(f"Track subscribed: {publication.name} from {participant.identity}, kind: {publication.kind}")
        
        ctx.room.on("participant_connected", on_participant_connected)
        ctx.room.on("track_published", on_track_published)
        ctx.room.on("track_subscribed", on_track_subscribed)
        
        # Log room participants
        logger.info(f"Room participants: {len(ctx.room.remote_participants)}")
        for participant in ctx.room.remote_participants.values():
            logger.info(f"Remote participant: {participant.identity}, tracks: {len(participant.track_publications)}")
            for pub in participant.track_publications.values():
                logger.info(f"  Track: {pub.name}, kind: {pub.kind}")
        
        # Start the session - this will run until the room disconnects
        # AgentSession.start() handles the entire conversation flow
        logger.info("Starting agent session...")
        try:
            # Call agent started callback before starting session
            await agent.on_agent_started()
            
            # Start the session with capture_run=True to block until complete
            # The session will automatically handle audio, STT, LLM, and TTS
            result = await session.start(agent, room=ctx.room, capture_run=True)
            logger.info(f"Agent session completed with result: {result}")
            
        except Exception as e:
            logger.error(f"Error during session: {e}", exc_info=True)
            raise
        finally:
            # Clean up session
            logger.info("Closing agent session...")
            await session.aclose()
            logger.info("Interview agent session closed")
        
        # Call agent ended callback
        agent.on_agent_ended()
        
    except Exception as e:
        logger.error(f"Error in interview agent: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Validate required environment variables
    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        logger.error(
            "Missing required environment variables: "
            "LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET"
        )
        raise ValueError("Missing required LiveKit configuration")
    
    if not OPENAI_API_KEY:
        logger.error("Missing required environment variable: OPENAI_API_KEY")
        raise ValueError("Missing OpenAI API key")
    
    # Run the agent with CLI
    # Using named agent with explicit dispatch via token
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="interview-agent",  # Named agent - requires explicit dispatch via token
        )
    )

