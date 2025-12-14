"""Configuration management for the auto-apply agent."""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# CAPTCHA Configuration
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "")
CAPTCHA_SERVICE = os.getenv("CAPTCHA_SERVICE", "2captcha")  # 2captcha, anticaptcha, capsolver

# Application Configuration
RESUME_FILE_PATH = os.getenv("RESUME_FILE_PATH", "./data/resume.pdf")
RESUME_JSON_PATH = os.getenv("RESUME_JSON_PATH", "./data/resume.json")

# Browser Configuration
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "60000"))  # 60 seconds default

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

