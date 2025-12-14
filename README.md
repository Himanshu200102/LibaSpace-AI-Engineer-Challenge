# AI Interview Platform

Two systems I built to automate parts of the hiring and job application process. Both are fully functional and handle real-world scenarios like error recovery, edge cases, and integration challenges.

## What's Here

1. **AI Mock Interview System** - Voice-based interview platform that actually conducts interviews. Built with LiveKit for real-time audio.

2. **Job Auto-Apply Agent** - Automates filling out job applications on sites like Lever and Greenhouse. Handles forms, answers questions intelligently, and even solves CAPTCHAs automatically.

Both work end-to-end and are structured so you can actually deploy and use them, not just demos.

---

## Demo Videos

Watch the systems in action:

- **AI Mock Interview Demo**: [Watch on Google Drive](https://drive.google.com/file/d/1NBLbIQG-rShZSz7luOxgNT0d6XuCiu4d/view?usp=sharing)
- **Auto-Apply Agent Demo**: [Watch on Google Drive](https://drive.google.com/file/d/162UftMPiaIUfiaTpnDM-2kd3nM413qPL/view?usp=sharing)

---

## Part 1: AI Mock Interview System

A voice interview system built with LiveKit. You can actually have a conversation with it—it conducts structured interviews with real-time voice interaction.

### What Makes It Work

- Real-time voice conversation using LiveKit for audio streaming
- State machine that handles interview stages smoothly (introduction → experience discussion)
- Uses LLM function calling so the AI can decide when to move between stages
- Timeout handling so conversations don't get stuck
- Structured logging so you can debug what's happening

### Tech Stack

- LiveKit Agents for the real-time audio infrastructure
- OpenAI for the LLM and text-to-speech
- AssemblyAI for speech-to-text (optional, falls back to OpenAI if not configured)
- Voice activity detection to know when someone is speaking

### How It Works

You connect via a web client, the agent greets you, and then walks through structured interview stages. It asks about your background, listens to your responses, and follows up naturally. The tricky part was handling stage transitions—I used LLM function calling so the AI decides when you've finished a section, with timeout fallbacks in case that doesn't work.

### Getting Started

📁 **Location**: [`part1_mock_interview/`](./part1_mock_interview/)

See the [detailed README](./part1_mock_interview/README.md) for:
- Complete setup instructions
- Architecture overview
- Testing guide
- Deployment instructions

---

## Part 3: Job Auto-Apply Agent

Automates the tedious process of applying to jobs. Fills out application forms, answers questions based on your resume, and handles CAPTCHAs so you don't have to.

### The Interesting Parts

- Chrome extension for CAPTCHA handling (makes it harder for sites to detect automation)
- LLM-powered question answering that actually reads your resume and generates appropriate responses
- Automatic CAPTCHA solving via 2Captcha API
- Works across different ATS platforms (Lever, Greenhouse, etc.) with extensible architecture

### Tech Stack

- Playwright for browser automation
- Chrome Extension (JavaScript) that runs in the browser context
- FastAPI server as a bridge between the extension and Python code
- OpenAI for generating answers to application questions
- 2Captcha for solving CAPTCHAs

### How It Works

Give it a job application URL and your resume data. It navigates to the page, fills out all the fields intelligently (basic info from your resume, complex questions using the LLM), uploads your resume PDF, solves any CAPTCHAs that show up, and submits the application. The Chrome extension was key here—it provides real browser context for CAPTCHA handling, which is way more reliable than trying to solve them through Playwright alone.

### Getting Started

📁 **Location**: [`part3_auto_apply_agent/`](./part3_auto_apply_agent/)

See the [detailed README](./part3_auto_apply_agent/README.md) for:
- Installation and setup
- Configuration guide
- Architecture details
- Usage instructions

---

## Architecture Decisions

I tried to keep things practical and maintainable:

**Modular Structure** - Both systems are split into logical modules. The interview system has separate components for state management, tools, and prompts. The auto-apply agent separates browser management, form handling, and CAPTCHA solving. Makes it easier to work with and extend.

**Error Handling** - Real error handling, not just try-catch blocks. The interview system has timeout mechanisms so conversations don't hang. The auto-apply agent has fallbacks if CAPTCHA solving fails or fields aren't detected correctly.

**Configuration** - Everything configurable via environment variables. API keys, timeouts, model choices—all externalized so you can deploy without code changes.

**Extensibility** - Adding new interview stages or ATS platforms doesn't require rewriting core code. The interview state machine makes it straightforward to add stages. The form handler uses strategies that work across different form structures.

---

## Quick Navigation

| System | Directory | Documentation |
|--------|-----------|---------------|
| AI Mock Interview | [`part1_mock_interview/`](./part1_mock_interview/) | [README](./part1_mock_interview/README.md) |
| Auto-Apply Agent | [`part3_auto_apply_agent/`](./part3_auto_apply_agent/) | [README](./part3_auto_apply_agent/README.md) |

---

## Technical Challenges I Solved

### Mock Interview System

**State Management** - Built a proper state machine so the interview flows through stages correctly. Prevents the agent from asking the same question multiple times or getting stuck in loops.

**Stage Transitions** - Used LLM function calling so the AI can decide when someone has finished talking about a topic. Also added timeout fallbacks because LLMs aren't always reliable.

**Real-time Audio** - LiveKit handles the heavy lifting, but getting voice activity detection right and managing turn-taking took some work.

### Auto-Apply Agent

**CAPTCHA Handling** - The hardest part. Regular Playwright automation gets detected. Built a Chrome extension that runs in the browser context, plus a bridge server so the extension can communicate with Python code. This approach actually works.

**Form Field Detection** - Different ATS systems use completely different HTML structures. Built multiple detection strategies that try different selectors and approaches until something works.

**Intelligent Answers** - For complex questions, the LLM reads both your resume and the job description to generate appropriate responses. Not just keyword matching.

---

## Requirements

Both systems require:
- Python 3.9+
- API keys (OpenAI required, others optional based on features)
- See individual READMEs for specific prerequisites

---

## Future Improvements

There's a lot you could add to both systems:

**Mock Interview:**
- Support for multiple languages
- Custom interview templates/question sets
- Analytics dashboard to track interview performance
- Integration with ATS systems to automatically schedule interviews

**Auto-Apply Agent:**
- More ATS platforms (currently optimized for Lever)
- Auto-parse resume from PDF instead of requiring JSON input
- Batch processing to apply to multiple jobs at once
- Track which applications got responses

Both READMEs have more detailed roadmaps if you're curious about specific implementation ideas.

---

## Setup

Each part has its own setup instructions. Check the individual READMEs for:
- Installation steps
- API key configuration
- How to run locally
- Deployment considerations

Both systems require Python 3.9+ and API keys (OpenAI at minimum, others are optional depending on which features you want to use).

---

Built as part of a technical assessment. Both systems work end-to-end and are structured for actual use, not just demos.

