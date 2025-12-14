# Job Auto-Apply Agent

An automated system that fills out and submits job applications on ATS platforms like Lever, Greenhouse, and Workday. It intelligently handles form fields, answers questions using your resume data, and even solves CAPTCHA challenges automatically.

## What This Does

Instead of manually filling out the same information across dozens of job applications, this agent does it for you. It reads job postings, fills out forms intelligently, handles various question types, and submits applications - all while solving CAPTCHA challenges automatically.

## Demo Video

See the system in action:

📹 **Demo Video**: [Watch on Google Drive](https://drive.google.com/file/d/162UftMPiaIUfiaTpnDM-2kd3nM413qPL/view?usp=sharing)

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- OpenAI API key (for intelligent question answering)
- 2Captcha API key (for CAPTCHA solving - optional but recommended)
- Your resume in PDF format

### Installation

First, clone or download this repository, then set up the environment:

```bash
# Navigate to the project directory
cd part3_auto_apply_agent

# Create a virtual environment (recommended)
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Configuration

1. **Set up environment variables**

Copy the example environment file and add your API keys:

```bash
# Windows
copy env.example .env

# Mac/Linux
cp env.example .env
```

Then edit `.env` and add your keys:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
CAPTCHA_API_KEY=your-2captcha-api-key-here

# Optional settings
HEADLESS=false
LOG_LEVEL=INFO
```

2. **Prepare your resume data**

Create a `data/` folder if it doesn't exist, then:

- Place your resume PDF as `data/resume.pdf`
- Create `data/resume.json` with your information (see `data/resume.json` for the format)

The JSON file should include your personal info, work experience, education, skills, and application preferences (like salary expectations, notice period, etc.).

### Running It

Once everything is set up, running the agent is simple:

```bash
python main.py <job_application_url>
```

For example:

```bash
python main.py https://jobs.lever.co/ekimetrics/d9d64766-3d42-4ba9-94d4-f74cdaf20065
```

The agent will:
1. Navigate to the job application page
2. Extract the job description
3. Fill out all form fields
4. Upload your resume
5. Handle any CAPTCHA challenges
6. Submit the application

You'll see progress logs in the terminal, and a detailed result will be saved to `lever_result.json` when it's done.

## How It Works

The system is built with several components working together:

### Core Components

**1. Agent Orchestrator (`core/agent.py`)**
The main coordinator that manages the entire application flow. It initializes all other components and sequences the steps: form filling, verification, CAPTCHA handling, and submission.

**2. Form Handler (`core/form_handler.py`)**
This is where the heavy lifting happens. It:
- Detects different field types (text inputs, dropdowns, radio buttons, checkboxes)
- Fills basic info directly from your resume JSON
- Uses LLM to answer complex questions intelligently
- Handles special cases like location autocomplete
- Fills diversity fields and consent checkboxes based on your preferences
- Uploads your resume PDF
- Verifies all fields are filled (with a second pass if needed)

**3. LLM Client (`core/llm_client.py`)**
Wraps OpenAI's API to answer questions based on your resume data and the job description. When the form handler encounters a question that can't be answered directly from your resume, it asks the LLM to generate an appropriate response.

**4. Resume Helper (`utils/resume.py`)**
Extracts specific information from your resume JSON file. It knows how to find salary expectations, notice period, visa status, languages, and handles default values for common questions.

**5. Browser Manager (`automation/browser.py`)**
Manages the Playwright browser instance. It:
- Launches Chrome with the CAPTCHA-solving extension loaded
- Starts the bridge server for extension communication
- Handles browser context and page management
- Cleans up resources when done

### CAPTCHA Solving System

One of the biggest challenges with automated form filling is CAPTCHA challenges. This system handles it with a three-part approach:

**Chrome Extension (`chrome_extension/`)**
A browser extension that runs on every page the browser visits. It:
- Detects when CAPTCHA widgets are present (reCAPTCHA, hCaptcha)
- Extracts the site keys needed to solve them
- Communicates with the bridge server to request solutions
- Injects solutions back into the form fields

**Bridge Server (`automation/captcha_bridge.py`)**
An HTTP server that acts as a communication layer between the JavaScript extension and the Python code. The extension can't directly call Python functions, so this server receives requests from the extension and forwards them to the CAPTCHA solver.

**CAPTCHA Solver (`automation/captcha_solver.py`)**
Integrates with the 2Captcha service API. When a CAPTCHA challenge is detected, it:
- Submits the challenge to 2Captcha
- Polls for the solution (usually takes 10-30 seconds)
- Returns the solution token back through the chain

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Job Application Page                     │
│                  (e.g., Lever, Greenhouse)                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent Orchestrator                         │
│                  (core/agent.py)                            │
│                                                             │
│  • Manages application flow                                │
│  • Coordinates all components                              │
│  • Handles errors and logging                              │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  Form Handler    │          │  Browser Manager │
│  (core/form_     │          │  (automation/    │
│   handler.py)    │          │   browser.py)    │
│                  │          │                  │
│  • Field detect  │          │  • Launch Chrome │
│  • Fill forms    │          │  • Load extension│
│  • Verify fields │          │  • Manage pages  │
│  • Upload resume │          └────────┬─────────┘
└──────┬───────────┘                   │
       │                               │
       ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│   LLM Client     │          │  Chrome Extension│
│  (core/llm_      │          │  (chrome_        │
│   client.py)     │          │   extension/)    │
│                  │          │                  │
│  • Answer Qs     │          │  • Detect CAPTCHA│
│  • Generate text │          │  • Extract keys  │
│  • Use resume    │          │  • Inject solution│
└──────────────────┘          └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  Bridge Server   │
                              │  (automation/    │
                              │   captcha_       │
                              │   bridge.py)     │
                              │                  │
                              │  • HTTP endpoint │
                              │  • Extension ↔   │
                              │    Python comm   │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  CAPTCHA Solver  │
                              │  (automation/    │
                              │   captcha_       │
                              │   solver.py)     │
                              │                  │
                              │  • 2Captcha API  │
                              │  • Poll for sol  │
                              └──────────────────┘
```

### Component Interaction

1. **Agent** initializes Browser Manager and starts the browser with extension
2. **Browser Manager** loads the extension and starts the bridge server
3. **Form Handler** fills fields using Resume Helper and LLM Client when needed
4. When CAPTCHA is detected, **Extension** communicates with **Bridge Server**
5. **Bridge Server** calls **CAPTCHA Solver** which uses 2Captcha API
6. Solution flows back through the chain and gets injected into the form
7. **Form Handler** verifies everything and submits

### Project Structure

```
part3_auto_apply_agent/
├── core/
│   ├── agent.py              # Main orchestrator
│   ├── form_handler.py       # Form filling logic
│   └── llm_client.py         # OpenAI API wrapper
├── automation/
│   ├── browser.py            # Browser management
│   ├── captcha_solver.py     # 2Captcha integration
│   └── captcha_bridge.py     # HTTP bridge server
├── chrome_extension/
│   ├── manifest.json         # Extension configuration
│   ├── content/
│   │   └── content-script.js # CAPTCHA detection & injection
│   └── background/
│       └── background.js     # Extension service worker
├── utils/
│   ├── resume.py             # Resume data helpers
│   └── config.py             # Configuration management
├── data/
│   ├── resume.json           # Your resume data
│   └── resume.pdf            # Your resume file
├── main.py                   # Entry point
└── requirements.txt          # Python dependencies
```

## Features

**Intelligent Form Filling**
The agent doesn't just blindly fill fields. It understands context - if a question asks about your experience with a specific technology, it extracts relevant info from your resume and formulates an answer using the LLM.

**Smart Field Detection**
Different ATS systems use different HTML structures. The form handler tries multiple strategies to find fields: by label text, by aria-labels, by common selectors. It also handles various field types including location autocomplete, multi-select dropdowns, and radio button groups.

**Two-Pass Verification**
After filling all fields, the agent does a second pass to check for any missed fields. If something wasn't filled correctly, it tries again.

**CAPTCHA Handling**
When CAPTCHA challenges appear (which they often do when automation is detected), the extension automatically detects them and solves them using the 2Captcha service.

**Configurable Preferences**
Your resume JSON includes application preferences - default answers for diversity questions, common yes/no questions, and consent checkboxes. This means you don't have to hardcode these choices.

**Error Handling**
The system handles various error scenarios gracefully - missing fields, CAPTCHA solving failures, network issues. It logs everything clearly so you know what happened.

## Configuration Details

### Resume JSON Format

Your `resume.json` should include:

- **personal_info**: Name, email, phone, location, LinkedIn, website
- **experience**: List of work experiences with company, position, dates, responsibilities, skills
- **education**: Institutions, degrees, graduation years
- **skills**: Programming languages, tools, technologies
- **salary_expectations**: Min/max salary range
- **notice_period**: How much notice you need to give
- **visa_status**: Work authorization status
- **application_preferences**: 
  - Diversity field defaults (gender, ethnicity, etc.)
  - Common question answers (how did you hear, start date, etc.)
  - Consent checkbox preferences

See `data/resume.json` for a complete example.

### Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key for LLM-powered responses
- `CAPTCHA_API_KEY` (optional): Your 2Captcha API key for automatic CAPTCHA solving
- `HEADLESS` (optional): Set to `true` to run browser in background, `false` to see it (default: `false`)
- `LOG_LEVEL` (optional): Logging verbosity - DEBUG, INFO, WARNING, ERROR (default: INFO)

## Troubleshooting

**"Extension not loading"**
Make sure the `chrome_extension/` directory exists and has all the required files. Check the logs for the exact error message.

**"CAPTCHA solving failed"**
If you see this, check:
- Your 2Captcha API key is correct in `.env`
- You have balance in your 2Captcha account
- The site key was extracted correctly (check logs)

The system will still try to submit the form even if CAPTCHA solving fails - sometimes forms don't actually require the CAPTCHA to be solved.

**"Fields not being filled"**
Check that your `resume.json` has the required fields. The agent will log which fields it's trying to fill - use those logs to see what's happening.

**"Browser not opening"**
If you want to see the browser, make sure `HEADLESS=false` in your `.env` file.

## Cost Considerations

- **OpenAI API**: Depends on usage, roughly $0.01-0.03 per application (for GPT-4o)
- **2Captcha**: About $0.003 per CAPTCHA solve (~$3 per 1000 applications)

For most use cases, this is significantly cheaper than the time you'd spend manually applying.

## Limitations

- Currently optimized for Lever job applications, though the architecture supports other ATS systems
- CAPTCHA solving requires an active 2Captcha account with balance
- Some forms may have unusual structures that require code adjustments
- Rate limiting: Be mindful of how many applications you submit to avoid being flagged

## Future Improvements

There are several areas where this could be extended and improved:

### Platform Support
- **More ATS systems**: Currently optimized for Lever, but the architecture supports extending to Greenhouse, Workday, and others. Each platform has different form structures that would need specific handlers.
- **Direct API integration**: Some ATS systems offer APIs that could be more reliable than form scraping.

### Intelligence & Accuracy
- **Better field mapping**: Use ML models to improve field detection accuracy across different form layouts.
- **Resume parsing**: Automatically extract resume data from PDF/DOCX files instead of requiring manual JSON input.
- **Job matching**: Analyze job descriptions and rank applications by fit before applying.
- **Answer quality**: Fine-tune LLM prompts to generate more tailored, higher-quality responses.

### CAPTCHA Handling
- **Multiple CAPTCHA services**: Support for AntiCaptcha, CapSolver, and other services beyond 2Captcha.
- **Solution caching**: Cache solutions for similar CAPTCHAs to reduce API calls and costs.
- **Better detection**: Improve site key extraction logic to handle edge cases.
- **CDP integration**: Use Chrome DevTools Protocol for more reliable extension communication.

### Scalability & Operations
- **Batch processing**: Apply to multiple jobs at once with proper rate limiting.
- **Queue system**: Background job processing for large-scale applications.
- **Scheduling**: Built-in scheduler to apply to jobs at specific times or dates.
- **Monitoring dashboard**: Web interface to track application status, success rates, and costs.

### User Experience
- **Configuration UI**: Web interface for editing resume data and preferences instead of JSON.
- **Application tracking**: Database to track all applications, responses, and follow-ups.
- **Email integration**: Monitor application emails and automatically respond to requests.
- **Profile management**: Support for multiple resume profiles and cover letter templates.

### Reliability
- **Better error recovery**: More sophisticated retry logic and error handling.
- **Form validation**: Pre-submit validation to catch errors before submission.
- **Screenshot capture**: Save screenshots of filled forms for verification.
- **Logging improvements**: Structured logging with better analysis tools.

### Cost Optimization
- **Smart CAPTCHA solving**: Only solve CAPTCHA when actually required for submission.
- **LLM cost reduction**: Cache common questions and answers, use cheaper models where possible.
- **Rate limiting**: Intelligent rate limiting to avoid being flagged while maximizing throughput.

### Security & Privacy
- **Credential management**: Secure storage of API keys and sensitive data.
- **Privacy controls**: Options to control what data is sent to external APIs.
- **Audit logging**: Track all actions for compliance and debugging.

## Contributing

This was built as part of a take-home challenge, but feel free to fork and extend it. The codebase is structured to make adding new features relatively straightforward - most components are modular and can be extended independently.

## License

Part of an AI Engineer take-home challenge submission.
