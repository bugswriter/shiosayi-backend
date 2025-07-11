import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

KOFI_VERIFICATION_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")

if not KOFI_VERIFICATION_TOKEN:
    print("WARNING: KOFI_VERIFICATION_TOKEN not set in environment variables. Webhook verification will fail.")

@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    data = request.get_json(silent=True)

    if data is None:
        raw_data = request.get_data(as_text=True)
        print(f"ERROR: Webhook received non-JSON or unparseable data. Raw data: {raw_data[:200]}...")
        return jsonify({"status": "error", "message": "Request body is not valid JSON or is empty"}), 400

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

    return jsonify({"status": "success", "message": "Webhook received and processed"}), 200

if __name__ == '__main__':
    print("Flask server starting...")
    print("Listening on http://127.0.0.1:5050/")
    print("Webhook endpoint: /webhook")
    print(f"Ko-fi Verification Token (from .env): {KOFI_VERIFICATION_TOKEN}")
    app.run(host='127.0.0.1', port=5050, debug=True)
