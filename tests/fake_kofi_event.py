# fake-kofi-event.py
import requests
import json
import os
import uuid
from datetime import datetime, timezone
from faker import Faker
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5001")
WEBHOOK_URL = f"{BASE_URL}/webhook"
KOFI_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
fake = Faker()

def generate_payload(email, tier, is_first_payment=True):
    # ... (This function is correct)
    payload = {
        "verification_token": KOFI_TOKEN,
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "Subscription",
        "is_public": True,
        "from_name": fake.name(),
        "message": fake.sentence(),
        "amount": "5.00" if tier == "keeper" else "10.00" if tier == "savior" else "3.00",
        "url": fake.url(),
        "email": email,
        "currency": "USD",
        "is_subscription_payment": True,
        "is_first_subscription_payment": is_first_payment,
        "kofi_transaction_id": str(uuid.uuid4()),
        "shop_items": None,
        "tier_name": tier,
        "shipping": None
    }
    return payload


def send_webhook(payload):
    """Sends the payload to the configured webhook URL."""
    try:
        # Ko-fi sends the JSON as a string inside a form field named 'data'
        form_data = {'data': json.dumps(payload)}
        
        print(f"Sending POST request to {WEBHOOK_URL}...")
        response = requests.post(WEBHOOK_URL, data=form_data, timeout=10)
        
        print("\n--- RESPONSE ---")
        print(f"Status Code: {response.status_code}")
        try:
            print("Response JSON:", response.json())
        except json.JSONDecodeError:
            print("Response Text:", response.text)
        print("----------------\n")
        
    except requests.exceptions.RequestException as e:
        print(f"\n--- ERROR ---")
        print(f"Failed to send request: {e}")
        print("----------------\n")

if __name__ == "__main__":
    print("--- Fake Ko-fi Event Sender ---")
    if not KOFI_TOKEN:
        print("ERROR: KOFI_VERIFICATION_TOKEN not found in .env file. Exiting.")
        exit(1)

    try:
        user_email = input("Enter the guardian's email: ").strip()
        user_tier = input("Enter the tier (lover, keeper, savior): ").strip().lower()

        if user_tier not in ['lover', 'keeper', 'savior']:
            print("Invalid tier. Please choose from 'lover', 'keeper', or 'savior'.")
            exit(1)
            
        is_first = input("Is this the first payment? (yes/no) [yes]: ").strip().lower() != 'no'

        payload = generate_payload(user_email, user_tier, is_first_payment=is_first)
        send_webhook(payload)
        
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
