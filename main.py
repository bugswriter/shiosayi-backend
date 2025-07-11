import os
import json # Import the json module to manually parse JSON
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Get Ko-fi verification token from environment variables
KOFI_VERIFICATION_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")

# Basic check to ensure the token is loaded
if not KOFI_VERIFICATION_TOKEN:
    print("WARNING: KOFI_VERIFICATION_TOKEN not set in environment variables. Webhook verification will fail.")

@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    """
    Handles incoming Ko-fi webhook requests.
    Attempts to parse the request body as JSON,
    even if the Content-Type header is not strictly 'application/json'.
    """
    data = None
    if request.is_json:
        # If Flask detects it as JSON, try to get it directly
        try:
            data = request.get_json()
        except Exception as e:
            # Catch potential errors during JSON parsing even if Content-Type is correct
            print(f"ERROR: Could not parse JSON from request.is_json (Content-Type was application/json): {e}")
            return jsonify({"status": "error", "message": "Invalid JSON format detected by Flask"}), 400
    else:
        # If not explicitly JSON (e.g., Content-Type missing or incorrect),
        # try to parse the raw data as JSON manually.
        try:
            raw_data = request.get_data(as_text=True)
            if raw_data: # Only attempt to parse if there's actual data
                data = json.loads(raw_data)
                print("INFO: Successfully parsed JSON from raw data (Content-Type might have been missing/incorrect).")
            else:
                print("ERROR: Webhook received empty data or non-JSON data.")
                return jsonify({"status": "error", "message": "Request must contain JSON data"}), 400
        except json.JSONDecodeError as e:
            # This means the raw data was not valid JSON
            print(f"ERROR: Webhook received non-JSON data or invalid JSON format: {e}")
            return jsonify({"status": "error", "message": "Request must be JSON or valid JSON"}), 400
        except Exception as e:
            # Catch any other unexpected errors during raw data processing
            print(f"ERROR: Unexpected error when processing non-JSON request: {e}")
            return jsonify({"status": "error", "message": "Failed to process request data"}), 400

    # If 'data' is still None after all parsing attempts, something went wrong
    if data is None:
        print("ERROR: Data could not be parsed from the incoming request.")
        return jsonify({"status": "error", "message": "Failed to parse request data"}), 400

    # --- Security Check: Verify the Ko-fi token ---
    received_token = data.get('verification_token')
    if received_token != KOFI_VERIFICATION_TOKEN:
        print(f"ERROR: Invalid verification token received: {received_token}")
        return jsonify({"status": "error", "message": "Invalid verification token"}), 403

    print("--- Ko-fi Webhook Received ---")
    print(f"Message ID: {data.get('message_id')}")
    print(f"Timestamp: {data.get('timestamp')}")
    print(f"Type: {data.get('type')}")
    print(f"From Name: {data.get('from_name')}")
    print(f"Amount: {data.get('amount')} {data.get('currency')}")
    print(f"Message: {data.get('message')}")
    print(f"URL: {data.get('url')}")
    print(f"Is Public: {data.get('is_public')}")
    print(f"Ko-fi Transaction ID: {data.get('kofi_transaction_id')}")

    # You can add your custom logic here based on the webhook data.
    # For example:
    # - Update a database
    # - Send a notification (email, Discord, etc.)
    # - Trigger other actions

    return jsonify({"status": "success", "message": "Webhook received and processed"}), 200

if __name__ == '__main__':
    # When running locally, Flask defaults to http://127.0.0.1:5000/
    # For Ko-fi to reach this, you'll need a public URL.
    # Tools like ngrok (https://ngrok.com/) can expose your local server to the internet.
    # Example: ngrok http 5050
    print("Flask server starting...")
    print("Listening on http://127.0.0.1:5050/")
    print("Webhook endpoint: /webhook")
    print(f"Ko-fi Verification Token (from .env): {KOFI_VERIFICATION_TOKEN}")
    app.run(host='127.0.0.1', port=5050, debug=True) # debug=True allows for automatic reloading on code changes
