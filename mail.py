import os
import resend
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
# This ensures that RESEND_API_KEY is available
load_dotenv()

# Configure logging for the email service
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailService:
    """
    A service class to manage sending emails using the Resend API.
    It supports different email templates.
    """
    def __init__(self):
        """
        Initializes the EmailService by setting the Resend API key
        from environment variables.
        """
        self.api_key = os.getenv("RESEND_API_KEY")
        if not self.api_key:
            logging.error("RESEND_API_KEY not found in environment variables. Please set it in your .env file.")
            raise ValueError("RESEND_API_KEY is not set.")
        resend.api_key = self.api_key
        logging.info("EmailService initialized successfully.")

    def _get_template_html(self, template_name: str, data: dict) -> str:
        """
        Generates the HTML content for a given email template.

        Args:
            template_name (str): The name of the template to use (e.g., 'api_key_email').
            data (dict): A dictionary containing data to populate the template.

        Returns:
            str: The generated HTML string for the email.
        """
        if template_name == 'api_key_email':
            user_name = data.get('user_name', 'Valued User')
            api_key = data.get('api_key', 'YOUR_API_KEY_HERE')
            # Basic HTML template for the API key email
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

    def send_email(self,
                   to_email: str,
                   subject: str,
                   template_name: str,
                   template_data: dict = None,
                   from_email: str = "Shiosayi <sys@shiosayi.org>"):
        """
        Sends an email using the specified template and data.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject line of the email.
            template_name (str): The name of the template to use (e.g., 'api_key_email').
            template_data (dict, optional): A dictionary containing data to populate the template. Defaults to None.
            from_email (str, optional): The sender's email address. Defaults to "Shiosayi <sys@shiosayi.org>".

        Returns:
            dict: The response from the Resend API if successful, None otherwise.
        """
        if template_data is None:
            template_data = {}

        html_content = self._get_template_html(template_name, template_data)

        try:
            r = resend.Emails.send({
                "from": from_email,
                "to": to_email,
                "subject": subject,
                "html": html_content
            })
            logging.info(f"Email sent successfully to {to_email} with subject '{subject}'. Response: {r}")
            return r
        except resend.ResendError as e:
            logging.error(f"Failed to send email to {to_email}. Resend API Error: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred while sending email to {to_email}: {e}")
            return None

# Example usage (for testing purposes, can be removed in production)
if __name__ == "__main__":
    # Create a dummy .env file for testing if it doesn't exist
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("RESEND_API_KEY=re_YOUR_RESEND_API_KEY_HERE\n")
        print("Created a dummy .env file. Please replace 're_YOUR_RESEND_API_KEY_HERE' with your actual Resend API Key.")
        print("Exiting. Please update the .env file and run again.")
        exit()

    # Initialize the EmailService
    email_service = EmailService()

    # --- Test Case 1: Send API Key Email ---
    print("\n--- Sending API Key Email ---")
    recipient = "mizuritu2007@gmail.com" # Replace with your actual test email
    user_name = "Mizuritu"
    generated_api_key = "SHIOSAYI-XYZ-123-ABC-456" # This would be generated by your system

    response = email_service.send_email(
        to_email=recipient,
        subject="Your Shiosayi API Key is Here!",
        template_name="api_key_email",
        template_data={
            "user_name": user_name,
            "api_key": generated_api_key
        }
    )

    if response:
        print(f"API Key Email sent! Response ID: {response.get('id')}")
    else:
        print("Failed to send API Key Email.")

    # --- Test Case 2: Send a generic email (unknown template) ---
    print("\n--- Sending Generic Email (Unknown Template) ---")
    response_generic = email_service.send_email(
        to_email=recipient,
        subject="Generic Test Email",
        template_name="unknown_template",
        template_data={}
    )
    if response_generic:
        print(f"Generic Email sent! Response ID: {response_generic.get('id')}")
    else:
        print("Failed to send Generic Email (as expected for unknown template).")
