# mail.py

import os
import resend
from resend.exceptions import ResendError
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailService:
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        if not self.api_key:
            logging.error("RESEND_API_KEY not found in environment variables. Please set it in your .env file.")
            raise ValueError("RESEND_API_KEY is not set.")
        resend.api_key = self.api_key
        # Define the 'from' address during initialization. For this to work in production,
        # you must verify the 'shiosayi.org' domain in your Resend account.
        self.from_address = "Shiosayi <sys@shiosayi.org>"
        logging.info("EmailService initialized successfully.")

    def _get_template_html(self, template_name: str, data: dict) -> str:
        if template_name == 'api_key_email':
            user_name = data.get('user_name', 'Valued User')
            api_key = data.get('api_key', 'YOUR_API_KEY_HERE')
            html_content = f"""
            <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #f9f9f9;">
                <h2 style="color: #333; text-align: center; margin-bottom: 20px;">Welcome to Shiosayi!</h2>
                <p style="color: #555; line-height: 1.6;">Dear {user_name},</p>
                <p style="color: #555; line-height: 1.6;">Thank you for subscribing to Shiosayi or supporting us via Ko-fi! We're thrilled to have you as part of our community.</p>
                <p style="color: #555; line-height: 1.6;">Your exclusive API Key is:</p>
                <div style="background-color: #e8f0fe; padding: 15px; border-radius: 8px; text-align: center; margin: 25px 0;">
                    <code style="font-family: 'Courier New', monospace; font-size: 1.1em; color: #007bff; word-break: break-all;">{api_key}</code>
                </div>
                <p style="color: #555; line-height: 1.6;">Please keep this key safe. You can use it to access our services and integrate with your applications.</p>
                <p style="color: #555; line-height: 1.6;">If you have any questions or need assistance, feel free to reach out to our support team.</p>
                <p style="color: #555; line-height: 1.6; margin-top: 30px;">Best regards,</p>
                <p style="color: #555; line-height: 1.6;">The Shiosayi Team</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;">
                <p style="color: #888; font-size: 0.8em; text-align: center;">Shiosayi <a href="mailto:sys@shiosayi.org" style="color: #007bff; text-decoration: none;">sys@shiosayi.org</a></p>
            </div>
            """
            return html_content
        else:
            logging.warning(f"Unknown email template: {template_name}")
            return "<p>No template found for this email type.</p>"

    def send_email(self, to_email: str, subject: str, template_name: str, template_data: dict = None):
        if template_data is None:
            template_data = {}

        html_content = self._get_template_html(template_name, template_data)
        
        # --- TEST MODE OVERRIDE ---
        # If TEST_MODE is active, send all emails to a designated test recipient
        # to avoid the 'Invalid `to` field' error from Resend.
        recipient = to_email
        if os.getenv("TEST_MODE") == "true":
            test_recipient = os.getenv("TEST_EMAIL_RECIPIENT", "delivered@resend.dev")
            logging.info(f"TEST MODE: Overriding recipient from '{to_email}' to '{test_recipient}'")
            recipient = test_recipient

        try:
            r = resend.Emails.send({
                "from": self.from_address,
                "to": recipient,
                "subject": subject,
                "html": html_content
            })
            logging.info(f"Email sent successfully to '{recipient}' (Original recipient was '{to_email}'). Subject: '{subject}'.")
            return r
        except ResendError as e:
            logging.error(f"Failed to send email to '{recipient}'. Resend API Error: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred while sending email to '{recipient}': {e}")
            return None
