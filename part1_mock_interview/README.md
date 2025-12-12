# AI Mock Interview System

A production-ready voice-based AI interview system built with LiveKit Agents. This system conducts structured mock interviews with candidates, guiding them through self-introduction and past experience discussions with smooth, natural transitions and intelligent fallback mechanisms.

## Overview

This project demonstrates a complete implementation of a real-time voice AI interview agent that can engage candidates in meaningful conversations. The system handles complex scenarios like stage transitions, timeout management, and conversation context tracking—all while maintaining a natural, human-like interaction flow.

The architecture is designed for production use, with robust error handling, comprehensive logging, and extensible design patterns that make it easy to add new interview stages or customize the conversation flow.

## Key Features

**Structured Interview Flow**
- Two-stage interview process: self-introduction and past experience discussion
- Smooth, natural transitions between stages using LLM function calling
- Intelligent timeout mechanisms ensure the conversation never stalls
- Context-aware follow-up questions that reference previous answers

**Production-Ready Architecture**
- Comprehensive error handling and recovery
- Structured JSON logging for easy monitoring and debugging
- State management prevents repetitive prompts and conversation loops
- Extensible design allows easy addition of new interview stages

**Real-Time Voice Interaction**
- LiveKit-powered real-time audio streaming
- Support for multiple STT providers (OpenAI, AssemblyAI)
- High-quality TTS with multiple voice options
- Professional web client included for testing and demos

## Architecture

The system is built on LiveKit Agents framework, which provides the infrastructure for real-time voice AI applications. Here's how the components work together:

**Core Components:**

1. **InterviewAgent** - The main agent class that orchestrates the interview flow. It extends LiveKit's `Agent` base class and implements callbacks for user messages, agent speech, and function calls.

2. **InterviewStateManager** - Manages the interview state machine, tracking the current stage, conversation context, and transition history. It validates transitions and prevents invalid state changes.

3. **Function Tools** - LLM-callable functions that enable the agent to make decisions about when to transition between stages. This allows the LLM to naturally determine when a candidate has finished their introduction or completed discussing their experience.

4. **System Prompts** - Stage-specific prompts that guide the LLM's behavior. Each stage has carefully crafted instructions that ensure the agent asks appropriate questions and transitions smoothly.

**How It Works:**

1. When a candidate connects, the agent starts in the greeting stage
2. After greeting, it automatically transitions to self-introduction
3. The agent listens actively, providing brief acknowledgments
4. When the LLM detects the candidate has finished (via function call), it transitions to past experience discussion
5. If the candidate is inactive for too long, a timeout mechanism triggers the transition automatically
6. After discussing past experiences, the agent concludes the interview

The timeout mechanism acts as a safety net, ensuring the conversation always progresses even if the LLM doesn't detect completion. This dual approach (LLM detection + timeout) provides reliability while maintaining natural flow.

## Project Structure

```
part1_mock_interview/
├── main.py                      # Entry point and LiveKit job handler
├── agent/
│   ├── interview_agent.py       # Main InterviewAgent class
│   └── state_manager.py         # State machine and conversation tracking
├── tools/
│   └── interview_tools.py       # LLM function tools for stage transitions
├── prompts/
│   └── system_prompts.py        # Stage-specific system prompts
├── config/
│   └── settings.py              # Configuration and environment variables
├── utils/
│   └── structured_logging.py    # JSON-structured logging utility
├── client/
│   ├── index.html               # Web client for testing
│   └── token-generator.html     # Token generation utility
├── generate_token.py            # Python script for token generation
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Setup and Installation

### Prerequisites

- Python 3.9 or higher
- LiveKit server (cloud or self-hosted)
- OpenAI API key (required for LLM and TTS)
- AssemblyAI API key (optional, for better STT)

### Step 1: Install Dependencies

```bash
cd part1_mock_interview
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# LiveKit Configuration (Required)
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-api-key-here

# AssemblyAI Configuration (Optional)
ASSEMBLYAI_API_KEY=your_assemblyai_key_here

# Interview Configuration (Optional)
SELF_INTRO_TIMEOUT=45
PAST_EXPERIENCE_TIMEOUT=60

# Model Configuration (Optional)
LLM_MODEL=gpt-3.5-turbo
TTS_VOICE=alloy
```

**Getting Your API Keys:**

1. **LiveKit**: Sign up at https://cloud.livekit.io/ and create a project. Get your URL, API key, and secret from the project dashboard.

2. **OpenAI**: Sign up at https://platform.openai.com/, go to API Keys section, and create a new key. Make sure your account has credits.

3. **AssemblyAI** (optional): Sign up at https://www.assemblyai.com/ and get your API key from the dashboard. If not provided, the system will use OpenAI STT.

### Step 3: Run the Agent

**Development mode (with hot reload):**
```bash
python main.py dev
```

**Production mode:**
```bash
python main.py start
```

You should see output indicating the agent has registered and is waiting for jobs.

## Testing the System

### Using the Web Client

A professional web client is included for testing. Here's how to use it:

1. **Start the agent** (as shown above)

2. **Generate an access token:**
   ```bash
   python generate_token.py interview-demo Candidate
   ```
   This will output a JWT token. Copy it.

3. **Open the client:**
   - Open `client/index.html` in your browser
   - Or use the token generator at `client/token-generator.html`

4. **Connect:**
   - Enter your LiveKit URL
   - Enter room name (e.g., "interview-demo")
   - Paste the generated token
   - Click "Connect"
   - Allow microphone access when prompted
   - Start speaking!

The agent will greet you and begin the interview. You can watch the conversation log in the client interface.

### Testing Different Scenarios

The system handles various scenarios gracefully:

- **Normal flow**: Complete each stage naturally - the agent transitions smoothly
- **Quick responses**: Fast transitions work correctly without cutting off
- **Long pauses**: Timeout mechanism triggers after the configured time
- **Interruptions**: Turn detection handles overlapping speech
- **Function calls**: Transitions work via LLM function calling

## Implementation in Your System

### Integration Steps

1. **Deploy the Agent**
   - Set up the agent on your server (EC2, GCP, Azure, etc.)
   - Ensure Python 3.9+ is installed
   - Install dependencies from `requirements.txt`
   - Configure environment variables
   - Run with `python main.py start` or use a process manager like systemd/supervisor

2. **Set Up LiveKit Infrastructure**
   - Use LiveKit Cloud (easiest) or self-host LiveKit server
   - Configure agent dispatch (automatic or explicit via tokens)
   - Set up monitoring and logging

3. **Integrate with Your Application**
   - Generate access tokens for candidates (use `generate_token.py` or implement in your backend)
   - Embed the web client in your application, or build a custom client using LiveKit SDK
   - Handle interview completion callbacks and store results

4. **Customize the Interview Flow**
   - Modify `prompts/system_prompts.py` to adjust questions and behavior
   - Add new stages by extending `InterviewStage` enum and adding prompts
   - Adjust timeouts in `.env` based on your needs
   - Customize the agent's personality and style in the prompts

### Customization Options

**Adding New Interview Stages:**
1. Add a new stage to `InterviewStage` enum in `agent/state_manager.py`
2. Add a prompt for the stage in `prompts/system_prompts.py`
3. Update transition logic in `InterviewAgent` class
4. Add function tools if needed for transitions

**Adjusting Timeouts:**
- Set `SELF_INTRO_TIMEOUT` and `PAST_EXPERIENCE_TIMEOUT` in `.env`
- Timeouts are in seconds
- The system will automatically transition if a candidate is inactive for this duration

**Changing LLM Model:**
- Set `LLM_MODEL` in `.env` (options: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, `gpt-4o`)
- `gpt-3.5-turbo` is cheaper and works well for this use case
- `gpt-4o` provides best quality but is more expensive

**Customizing Voice:**
- Set `TTS_VOICE` in `.env` (options: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`)
- All voices are high-quality and natural-sounding

### Production Considerations

**Monitoring:**
- The system outputs structured JSON logs that can be easily parsed
- Logs include stage transitions, user/agent speech, function calls, and errors
- Integrate with your logging infrastructure (ELK, Datadog, etc.)

**Scaling:**
- Each agent instance can handle multiple concurrent interviews
- Use LiveKit Cloud's auto-scaling or deploy multiple agent instances
- Monitor resource usage and scale based on demand

**Error Handling:**
- The system includes comprehensive error handling
- Errors are logged with context for debugging
- The agent gracefully handles disconnections and API failures

**Security:**
- Never commit `.env` file (it's in `.gitignore`)
- Use different API keys for development and production
- Rotate keys regularly
- Implement proper access control for token generation

## Troubleshooting

**Agent not connecting:**
- Verify LiveKit credentials in `.env` are correct
- Check that your LiveKit server is accessible
- Review logs for connection errors
- Ensure agent is registered (check logs for "registered worker")

**Transitions not working:**
- Check OpenAI API key is valid and has credits
- Verify function tools are being called (check logs for "function_call" events)
- Review timeout settings - they might be too short
- Check that the LLM model supports function calling

**Audio issues:**
- Ensure microphone permissions are granted in the browser
- Check STT provider API keys are valid
- Verify network connectivity
- Try a different STT provider (switch between OpenAI and AssemblyAI)

**API quota errors:**
- Check your OpenAI account has sufficient credits
- Consider using `gpt-3.5-turbo` instead of `gpt-4o` to reduce costs
- Monitor API usage and set up billing alerts

## Technical Details

### State Management

The system uses a state machine pattern to manage interview stages. Valid transitions are:
- Greeting → Self-Introduction (automatic after greeting)
- Self-Introduction → Past Experience (via function call or timeout)
- Past Experience → Closing (via function call or timeout)

Invalid transitions are prevented, and all transitions are logged with context.

### Function Calling

The LLM uses function calling to make decisions about stage transitions. When the agent detects a candidate has finished their introduction, it calls `transition_to_past_experience()`. This allows for natural, context-aware transitions rather than rigid time-based rules.

### Timeout Mechanism

As a fallback, the system monitors time spent in each stage. If a candidate is inactive for the configured timeout period, the system automatically transitions. This ensures the conversation always progresses, even if the LLM doesn't detect completion.

### Conversation Context

The system tracks conversation context across stages, storing user responses and key information. This allows the agent to reference previous answers naturally and ask contextual follow-up questions.

## Why This Implementation

This project demonstrates several important engineering principles:

**Production-Ready Code**: Not a prototype or proof-of-concept, but a system designed for real-world use with proper error handling, logging, and monitoring.

**Extensible Architecture**: The code is organized in a way that makes it easy to add new features, stages, or customize behavior without major refactoring.

**Robust State Management**: The state machine pattern ensures reliable transitions and prevents edge cases that could break the interview flow.

**Intelligent Fallbacks**: Multiple mechanisms (LLM detection + timeout) ensure the system works reliably even when individual components have issues.

**Comprehensive Logging**: Structured logging makes it easy to debug issues and monitor system behavior in production.

## Next Steps

To extend this system, consider:

- Adding more interview stages (technical questions, behavioral questions, etc.)
- Integrating with ATS systems to store interview results
- Adding analytics and reporting dashboards
- Implementing multi-language support
- Adding video capabilities for video interviews
- Creating mobile clients for iOS/Android

The architecture is designed to support these extensions without major refactoring.

## License

Part of the AI Engineer take-home challenge.
