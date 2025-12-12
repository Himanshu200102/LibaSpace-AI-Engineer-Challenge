"""Generate LiveKit token with agent dispatch using the official SDK."""
import asyncio
from livekit import api
from livekit.api import AccessToken, VideoGrants, RoomConfiguration, RoomAgentDispatch
from config.settings import LIVEKIT_API_KEY, LIVEKIT_API_SECRET


def generate_token_with_agent_dispatch(
    room_name: str = "interview-demo",
    participant_name: str = "Candidate"
) -> str:
    """
    Generate a LiveKit access token with agent dispatch configuration.
    
    Args:
        room_name: Name of the room
        participant_name: Name/identity of the participant
        
    Returns:
        JWT token string
    """
    # Create access token
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(participant_name) \
        .with_name(participant_name) \
        .with_grants(VideoGrants(
            room=room_name,
            room_join=True,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        ))
    
    # Add room configuration with agent dispatch
    room_config = RoomConfiguration(
        agents=[
            RoomAgentDispatch(
                agent_name="interview-agent",
                metadata='{"participant": "' + participant_name + '"}'
            )
        ]
    )
    token.with_room_config(room_config)
    
    # Generate JWT
    jwt_token = token.to_jwt()
    return jwt_token


if __name__ == "__main__":
    import sys
    
    room_name = sys.argv[1] if len(sys.argv) > 1 else "interview-demo"
    participant_name = sys.argv[2] if len(sys.argv) > 2 else "Candidate"
    
    token = generate_token_with_agent_dispatch(room_name, participant_name)
    print("\n" + "="*60)
    print("LIVEKIT TOKEN WITH AGENT DISPATCH")
    print("="*60)
    print(f"Room: {room_name}")
    print(f"Participant: {participant_name}")
    print(f"Agent: interview-agent")
    print("="*60)
    print("\nToken:")
    print(token)
    print("\n" + "="*60)
    print("Copy this token and use it in the client to connect.")
    print("The agent will automatically join when you connect!")
    print("="*60 + "\n")

