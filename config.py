import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Configuration class for the Flask application.
    Loads sensitive data from environment variables.
    """
    KOFI_VERIFICATION_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "shiosayi_system.db") # Default if not set in .env
    RESEND_API_KEY = os.getenv("RESEND_API_KEY") # This is also used by mail.py directly

    # Basic validation for essential configurations
    if not KOFI_VERIFICATION_TOKEN:
        print("WARNING: KOFI_VERIFICATION_TOKEN not set in environment variables. Webhook verification will fail.")
    if not RESEND_API_KEY:
        print("WARNING: RESEND_API_KEY not set in environment variables. Email service may not function.")
