import json
import uuid
from flask import Blueprint, request, jsonify
from urllib.parse import parse_qs
import logging

from config import Config
from database import DatabaseManager
from mail import EmailService # Import the renamed EmailService

# Create a Blueprint for API routes
api_bp = Blueprint('api', __name__)

# Initialize services (these will be created once when the blueprint is registered)
db_manager = DatabaseManager()
email_service = EmailService()

# Configure logging for routes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@api_bp.route('/webhook', methods=['POST'])
def kofi_webhook():
    """
    Handles incoming Ko-fi webhook notifications.
    Parses the data, verifies the token, stores it in the database,
    and sends an email for subscriptions/memberships.
    """
    data = None
    content_type = request.headers.get('Content-Type', '')

    # Attempt to parse incoming data based on Content-Type
    if 'application/json' in content_type:
        data = request.get_json(silent=True)
    elif 'application/x-www-form-urlencoded' in content_type:
        raw_body = request.get_data(as_text=True)
        if raw_body.startswith('data='):
            try:
                parsed_qs = parse_qs(raw_body)
                raw_json_string = parsed_qs.get('data', [''])[0]
                if raw_json_string:
                    data = json.loads(raw_json_string)
                    logging.info("Successfully parsed JSON from 'data' form field via parse_qs.")
                else:
                    logging.error("Form-urlencoded request received, 'data' field is empty after parsing.")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from 'data' form field (parse_qs): {e}")
            except Exception as e:
                logging.error(f"Unexpected error processing form-urlencoded data: {e}")
        else:
            logging.error("Form-urlencoded request received, but body does not start with 'data='.")
    else:
        raw_data = request.get_data(as_text=True)
        if raw_data:
            try:
                data = json.loads(raw_data)
                logging.info("Successfully parsed JSON from raw data (unexpected Content-Type).")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from raw data (Content-Type: {content_type}): {e}")
        else:
            logging.error(f"Request received with Content-Type: {content_type} and no data.")

    if data is None:
        final_raw_data = request.get_data(as_text=True)
        logging.error(f"Webhook received non-JSON or unparseable data. Content-Type: {content_type}, Raw data: '{final_raw_data}'")
        return jsonify({"status": "error", "message": "Request body is not valid JSON or is empty"}), 400

    # Verify Ko-fi webhook token
    received_token = data.get('verification_token')
    if received_token != Config.KOFI_VERIFICATION_TOKEN:
        logging.error(f"Invalid verification token received: {received_token}")
        return jsonify({"status": "error", "message": "Invalid verification token"}), 403

    logging.info(f"--- Ko-fi Webhook Received --- Message ID: {data.get('message_id')}, Type: {data.get('type')}")

    # Store data in SQLite database
    db_success = db_manager.insert_webhook_data(data)
    if not db_success:
        # If it's a duplicate, we still return success to Ko-fi to avoid retries
        logging.warning("Webhook data was a duplicate or failed to insert, but acknowledging success to Ko-fi.")
        # You might choose to return a 500 here if database storage is absolutely critical for further processing
        # return jsonify({"status": "error", "message": "Failed to store data"}), 500

    # Check if it's a subscription payment or first subscription payment
    is_subscription = data.get('is_subscription_payment')
    is_first_subscription = data.get('is_first_subscription_payment')
    user_email = data.get('email')
    user_name = data.get('from_name')
    tier_name = data.get('tier_name') # For monthly tier membership

    # Send email if it's a relevant event and email is available
    if (is_subscription or is_first_subscription or tier_name) and user_email:
        logging.info(f"Detected subscription/tier payment for {user_name} ({user_email}). Preparing to send API key email.")
        # Generate API Key (this logic should be robust and unique in a real system)
        generated_api_key = f"SHIOSAYI-{uuid.uuid4().hex[:12].upper()}"
        logging.info(f"Generated API Key for {user_name}: {generated_api_key}")

        email_subject = "Welcome to Shiosayi! Your API Key is Here!"
        if tier_name:
            email_subject = f"Welcome to Shiosayi {tier_name} Tier! Your API Key is Here!"

        email_response = email_service.send_email(
            to_email=user_email,
            subject=email_subject,
            template_name="api_key_email",
            template_data={
                "user_name": user_name,
                "api_key": generated_api_key
            }
        )

        if email_response:
            logging.info(f"API Key Email sent to {user_email}. Resend ID: {email_response.get('id')}")
        else:
            logging.error(f"Failed to send API Key Email to {user_email}.")
            # You might want to log this failure for manual follow-up
    else:
        logging.info("Webhook event is not a subscription/tier payment or email is missing. No API key email sent.")

    return jsonify({"status": "success", "message": "Webhook received and processed"}), 200

# You can add more routes here for other API endpoints
# @api_bp.route('/some_other_endpoint', methods=['GET'])
# def some_other_function():
#     return jsonify({"message": "This is another API endpoint"})
