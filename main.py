import os
import json
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import parse_qs

load_dotenv()

app = Flask(__name__)
CORS(app)

KOFI_VERIFICATION_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
DATABASE = 'kofi_webhooks.db' # SQLite database file

if not KOFI_VERIFICATION_TOKEN:
    print("WARNING: KOFI_VERIFICATION_TOKEN not set in environment variables. Webhook verification will fail.")

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            timestamp TEXT,
            type TEXT,
            is_public INTEGER,
            from_name TEXT,
            message TEXT,
            amount TEXT,
            currency TEXT,
            url TEXT,
            email TEXT,
            is_subscription_payment INTEGER,
            is_first_subscription_payment INTEGER,
            kofi_transaction_id TEXT,
            shop_items TEXT, -- Stored as JSON string
            tier_name TEXT,
            shipping TEXT, -- Stored as JSON string
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    data = None
    content_type = request.headers.get('Content-Type', '')

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
                    print("INFO: Successfully parsed JSON from 'data' form field via parse_qs.")
                else:
                    print("ERROR: Form-urlencoded request received, 'data' field is empty after parsing.")
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode JSON from 'data' form field (parse_qs): {e}")
            except Exception as e:
                print(f"ERROR: Unexpected error processing form-urlencoded data: {e}")
        else:
            print("ERROR: Form-urlencoded request received, but body does not start with 'data='.")
    else:
        raw_data = request.get_data(as_text=True)
        if raw_data:
            try:
                data = json.loads(raw_data)
                print("INFO: Successfully parsed JSON from raw data (unexpected Content-Type).")
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode JSON from raw data (Content-Type: {content_type}): {e}")
        else:
            print(f"ERROR: Request received with Content-Type: {content_type} and no data.")

    if data is None:
        final_raw_data = request.get_data(as_text=True)
        print(f"ERROR: Webhook received non-JSON or unparseable data.")
        print(f"Final Content-Type: {content_type}")
        print(f"Final Raw data received: '{final_raw_data}'")
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

    # --- Store data in SQLite ---
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO webhooks (
                message_id, timestamp, type, is_public, from_name, message,
                amount, currency, url, email, is_subscription_payment,
                is_first_subscription_payment, kofi_transaction_id,
                shop_items, tier_name, shipping
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('message_id'),
            data.get('timestamp'),
            data.get('type'),
            int(data.get('is_public', False)), # Convert boolean to int (0 or 1)
            data.get('from_name'),
            data.get('message'),
            data.get('amount'),
            data.get('currency'),
            data.get('url'),
            data.get('email'),
            int(data.get('is_subscription_payment', False)),
            int(data.get('is_first_subscription_payment', False)),
            data.get('kofi_transaction_id'),
            json.dumps(data.get('shop_items')) if data.get('shop_items') is not None else None, # Store as JSON string
            data.get('tier_name'),
            json.dumps(data.get('shipping')) if data.get('shipping') is not None else None # Store as JSON string
        ))
        conn.commit()
        conn.close()
        print("INFO: Webhook data successfully stored in SQLite database.")
    except sqlite3.IntegrityError:
        print(f"WARNING: Duplicate message_id '{data.get('message_id')}' received. Data not inserted.")
    except Exception as e:
        print(f"ERROR: Failed to store webhook data in database: {e}")
        # You might want to return a 500 error here if database storage is critical
        # return jsonify({"status": "error", "message": "Failed to store data"}), 500

    return jsonify({"status": "success", "message": "Webhook received and processed"}), 200

if __name__ == '__main__':
    init_db() # Initialize the database when the app starts
    print("Flask server starting...")
    print("Listening on http://127.0.0.1:5050/")
    print("Webhook endpoint: /webhook")
    print(f"Ko-fi Verification Token (from .env): {KOFI_VERIFICATION_TOKEN}")
    app.run(host='127.0.0.1', port=5050, debug=True)

