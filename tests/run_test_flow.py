# run_test_flow.py
import requests
import os
import json
import shlex  # Used for safely quoting shell arguments
from faker import Faker
from dotenv import load_dotenv

# Import the functions from our webhook engine
import fake_kofi_event as kofi_engine

# --- Configuration & Setup ---
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5001")
ADMIN_TOKEN = os.getenv("ADMIN_API_TOKEN")
fake = Faker()
TEST_STATE = {} # Stores state like email, token for the test run

# --- Helper Functions ---
def print_step(num, title, description=""):
    print("\n" + "="*70)
    print(f"   STEP {num}: {title.upper()}")
    print("="*70)
    if description:
        print(f"   {description}")

def prompt_to_continue():
    input("\n   ... Press Enter to proceed to the next step ...\n")

def generate_curl_command(method, url, headers=None, form_data=None):
    """Generates a copy-pasteable curl command for debugging."""
    command = f"curl -X {method.upper()}"
    
    if headers:
        for key, value in headers.items():
            command += f" -H {shlex.quote(f'{key}: {value}')}"
            
    if form_data:
        # Special handling for Ko-fi's url-encoded form data
        # The value of the 'data' key is a JSON string
        payload_str = form_data.get('data', '{}')
        command += f" --data-urlencode {shlex.quote(f'data={payload_str}')}"

    command += f" {shlex.quote(url)}"
    return command

def check_api_response(response, expected_status_code):
    """A clear pass/fail check for API calls."""
    if response is None:
        print("❌ FAILED: API call did not receive a response (likely a connection error).")
        return False, None
        
    print(f"   API Status Code: {response.status_code}")
    if response.status_code == expected_status_code:
        print(f"✅ PASSED: Received expected HTTP status {expected_status_code}.")
        try:
            return True, response.json()
        except requests.exceptions.JSONDecodeError:
            return True, response.text
    else:
        print(f"❌ FAILED: Expected HTTP {expected_status_code}, but got {response.status_code}.")
        print(f"   Response: {response.text}")
        return False, None

# --- Test Case Functions ---

def step_1_create_new_user():
    print_step(1, "Create a New 'Lover' Tier User", 
               "We will send a 'first payment' webhook to create a new guardian.")
    TEST_STATE['email'] = fake.email()
    print(f"   Generated fake email for this test: {TEST_STATE['email']}")
    
    payload = kofi_engine.generate_payload(TEST_STATE['email'], 'lover', is_first_payment=True)
    form_data = {'data': json.dumps(payload)}
    
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('POST', f"{BASE_URL}/webhook", form_data=form_data))
    print("-" * 50)
    
    print("\n   (Script is now executing this request...)")
    response = requests.post(f"{BASE_URL}/webhook", data=form_data)
    check_api_response(response, 200)

def step_2_get_api_token():
    print_step(2, "Retrieve API Token",
               "The API token was created. For this test, you must find it.")
    print(f"   ACTION REQUIRED: Please find the API token for the user with email '{TEST_STATE['email']}'.")
    print("   (Check your test email inbox, server logs, or query the database).")
    token = input("   Enter the API token: ").strip()
    if not token: exit("!! No token entered. Aborting test.")
    TEST_STATE['token'] = token

def step_3_verify_initial_state():
    print_step(3, "Verify Initial State via /auth")
    url = f"{BASE_URL}/auth?token={TEST_STATE['token']}"
    
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('GET', url))
    print("-" * 50)
    
    response = requests.get(url)
    passed, data = check_api_response(response, 200)
    if passed and data.get('tier') == 'lover' and not data.get('films'):
        print("✅ VERIFIED: User is 'lover' tier with 0 adopted films.")

def step_4_adopt_first_film():
    print_step(4, "Adopt a Film (Should Succeed)")
    film_id = input("   ACTION REQUIRED: Enter the ID of an 'orphan' film: ").strip()
    if not film_id: exit("!! No film ID entered. Aborting.")
    
    url = f"{BASE_URL}/adopt/{film_id}?TOKEN={TEST_STATE['token']}"
    
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('POST', url))
    print("-" * 50)
    
    response = requests.post(url)
    check_api_response(response, 200)

def step_5_test_tier_limit():
    print_step(5, "Test Tier Limit (Should Fail)",
               "Attempting to adopt a second film, which should be blocked for the 'lover' tier.")
    film_id = input("   ACTION REQUIRED: Enter the ID of a DIFFERENT 'orphan' film: ").strip()
    if not film_id: exit("!! No film ID entered. Aborting.")
    
    url = f"{BASE_URL}/adopt/{film_id}?TOKEN={TEST_STATE['token']}"
    
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('POST', url))
    print("-" * 50)
    
    response = requests.post(url)
    check_api_response(response, 403)

def step_6_upgrade_tier():
    print_step(6, "Upgrade User to 'Savior' Tier",
               "Sending a 'subsequent payment' webhook with a new tier name.")
    payload = kofi_engine.generate_payload(TEST_STATE['email'], 'savior', is_first_payment=False)
    form_data = {'data': json.dumps(payload)}

    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('POST', f"{BASE_URL}/webhook", form_data=form_data))
    print("-" * 50)
    
    response = requests.post(f"{BASE_URL}/webhook", data=form_data)
    check_api_response(response, 200)

def step_7_verify_upgrade_and_adopt():
    print_step(7, "Verify Upgrade and Adopt a Second Film")
    # Verify tier change
    print("   Verifying tier via /auth...")
    url = f"{BASE_URL}/auth?token={TEST_STATE['token']}"
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('GET', url))
    print("-" * 50)
    response = requests.get(url)
    passed, data = check_api_response(response, 200)
    if not (passed and data.get('tier') == 'savior'):
        exit(f"❌ VERIFICATION FAILED: User tier is {data.get('tier')}, expected 'savior'.")
    print("✅ VERIFIED: User is now 'savior' tier.")
    
    # Adopt another film
    film_id = input("\n   ACTION REQUIRED: Enter the ID of another 'orphan' film to adopt: ").strip()
    if not film_id: exit("!! No film ID entered. Aborting.")
    
    url = f"{BASE_URL}/adopt/{film_id}?TOKEN={TEST_STATE['token']}"
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('POST', url))
    print("-" * 50)
    response = requests.post(url)
    check_api_response(response, 200)

def step_8_run_housekeeping():
    print_step(8, "Test Subscription Cancellation (via Housekeeping)")
    print(f"   ACTION REQUIRED: In your database, find the guardian with email '{TEST_STATE['email']}' and change their 'last_paid_at' date to be more than 35 days in the past (e.g., '2024-01-01').")
    input("   ... Press Enter once you have manually updated the database ...")
    
    if not ADMIN_TOKEN: exit("!! ADMIN_API_TOKEN not set in .env. Aborting.")
    
    headers = {'Authorization': f'Bearer {ADMIN_TOKEN}'}
    url = f"{BASE_URL}/admin/housekeeping"
    
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('POST', url, headers=headers))
    print("-" * 50)

    response = requests.post(url, headers=headers)
    check_api_response(response, 200)

def step_9_final_verification():
    print_step(9, "Final Verification",
               "The user's token should now be invalid because housekeeping deleted them.")
    url = f"{BASE_URL}/auth?token={TEST_STATE['token']}"
    
    print("\n   👇 Generated curl command for this action:")
    print("-" * 50)
    print(generate_curl_command('GET', url))
    print("-" * 50)
    
    response = requests.get(url)
    check_api_response(response, 401)
    print("✅ VERIFIED: The lapsed guardian has been successfully removed from the system.")

if __name__ == "__main__":
    print("\n" + "#"*70)
    print("### Shiosayi Backend Interactive Test Suite ###")
    print("#"*70)
    print("\nIMPORTANT: Your previous test failed with a 403 Forbidden error.")
    print("This almost always means the 'KOFI_VERIFICATION_TOKEN' in your local .env file")
    print("does NOT match the token on your server (sys.shiosayi.org).")
    print("This script will generate `curl` commands so you can see the exact data being sent.")
    
    try:
        # Define the sequence of test functions to run
        test_sequence = [
            step_1_create_new_user,
            step_2_get_api_token,
            step_3_verify_initial_state,
            step_4_adopt_first_film,
            step_5_test_tier_limit,
            step_6_upgrade_tier,
            step_7_verify_upgrade_and_adopt,
            step_8_run_housekeeping,
            step_9_final_verification
        ]
        
        for i, test_func in enumerate(test_sequence):
            test_func()
            if i < len(test_sequence) - 1:
                prompt_to_continue()

        print("\n" + "*"*70)
        print("🎉   ALL TEST SCENARIOS COMPLETED!   🎉")
        print("*"*70)

    except (KeyboardInterrupt, EOFError):
        print("\n\nTest run aborted by user. Exiting.")
    except Exception as e:
        print(f"\n\n!! An unexpected error occurred: {e}")
