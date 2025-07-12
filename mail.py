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
            raise ValueError("RESEND_API_KEY is not set.")
        resend.api_key = self.api_key
        self.from_address = "Shiosayi <sys@shiosayi.org>"
        logging.info("EmailService initialized successfully.")

    def _get_template_html(self, template_name: str, data: dict) -> str:
        # We now use one flexible template
        if template_name == 'guardian_welcome_email':
            user_name = data.get('user_name', 'Guardian')
            tier_name = data.get('tier_name', 'Lover').capitalize()
            api_key = data.get('api_key', 'YOUR_API_KEY_HERE')
            
            # Dynamic title based on whether it's an upgrade
            title = data.get('title', "Welcome to the Shiosayi Community!")

            html_content = f"""
            <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #f9f9f9;">
                <h2 style="color: #333; text-align: center; margin-bottom: 20px;">{title}</h2>
                <p style="color: #555; line-height: 1.6;">Hello {user_name},</p>
                <p style="color: #555; line-height: 1.6;">Thank you for your incredible support! You are now officially a <strong>{tier_name}</strong> Tier Guardian. We're thrilled to have you with us on this journey to preserve rare films.</p>
                <p style="color: #555; line-height: 1.6;">Your personal API Key is below. This is your key to accessing the archive and adopting films. Keep it secret, keep it safe!</p>
                <div style="background-color: #e8f0fe; padding: 15px; border-radius: 8px; text-align: center; margin: 25px 0;">
                    <code style="font-family: 'Courier New', monospace; font-size: 1.1em; color: #007bff; word-break: break-all;">{api_key}</code>
                </div>
                <p style="color: #555; line-height: 1.6;">As a {tier_name} Guardian, you can adopt and protect films that need a home. Thank you for making a real difference.</p>
                <p style="color: #555; line-height: 1.6; margin-top: 30px;">Warmly,</p>
                <p style="color: #555; line-height: 1.6;">The Shiosayi Team</p>
            </div>
            """
            return html_content
        else:
            logging.warning(f"Unknown email template: {template_name}")
            return "<p>No template found for this email type.</p>"

    def send_email(self, to_email: str, subject: str, template_name: str, template_data: dict = None):
        if template_data is None: template_data = {}

        html_content = self._get_template_html(template_name, template_data)
        
        recipient = to_email
        if os.getenv("TEST_MODE") == "true":
            test_recipient = os.getenv("TEST_EMAIL_RECIPIENT", "delivered@resend.dev")
            logging.info(f"TEST MODE: Overriding recipient from '{to_email}' to '{test_recipient}'")
            recipient = test_recipient

        try:
            r = resend.Emails.send({
                "from": self.from_address, "to": recipient, "subject": subject, "html": html_content
            })
            logging.info(f"Email sent successfully to '{recipient}' (Original: '{to_email}').")
            return r
        except ResendError as e:
            logging.error(f"Failed to send email to '{recipient}'. Resend API Error: {e}")
            return None
