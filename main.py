import os
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
from dotenv import load_dotenv # Import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Get Ko-fi verification token from environment variables
# It's crucial to verify the 'verification_token' to ensure the request
# is legitimate and coming from Ko-fi.
KOFI_VERIFICATION_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")

# Basic check to ensure the token is loaded
if not KOFI_VERIFICATION_TOKEN:
    print("WARNING: KOFI_VERIFICATION_TOKEN not set in environment variables. Webhook verification will fail.")

@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    """
    Handles incoming Ko-fi webhook requests.
    """
    if request.is_json:
        data = request.get_json()

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
    else:
        print("ERROR: Webhook received non-JSON data.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

if __name__ == '__main__':
    # When running locally, Flask defaults to http://127.0.0.1:5000/
    # For Ko-fi to reach this, you'll need a public URL.
    # Tools like ngrok (https://ngrok.com/) can expose your local server to the internet.
    # Example: ngrok http 7070
    print("Flask server starting...")
    print("Listening on http://127.0.0.1:7070/")
    print("Webhook endpoint: /webhook")
    print(f"Ko-fi Verification Token (from .env): {KOFI_VERIFICATION_TOKEN}")
    app.run(host='127.0.0.1', port=7070, debug=True) # debug=True allows for automatic reloading on code changes

