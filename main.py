from flask import Flask, request, jsonif

app = Flask(__name__)

# Replace with your actual Ko-fi verification token
# This token is used to ensure the request is coming from Ko-fi
KOFI_VERIFICATION_TOKEN = "e58df006-d830-4114-96e9-6bbbfcb2b776" # This is from your example image

@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    """
    Handles incoming Ko-fi webhook requests.
    """
    if request.is_json:
        data = request.get_json()

        # --- Security Check: Verify the Ko-fi token ---
        # It's crucial to verify the 'verification_token' to ensure the request
        # is legitimate and coming from Ko-fi.
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
    # Example: ngrok http 5000
    print("Flask server starting...")
    print("Listening on http://127.0.0.1:5000/")
    print("Webhook endpoint: /webhook")
    print(f"Ko-fi Verification Token: {KOFI_VERIFICATION_TOKEN}")
    app.run(debug=True) # debug=True allows for automatic reloading on code changes
