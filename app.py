import os
import logging
import json
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, abort, render_template, flash, redirect, url_for
from flask import current_app, send_from_directory
from dotenv import load_dotenv

load_dotenv()
import services
import database
import utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# --- CONFIGURATION ---
app.config['DATABASE'] = os.getenv("DATABASE_FILENAME", "shiosayi.db")
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY') # Will be checked below
database.init_app(app)

# --- LOAD SECRETS AND SETTINGS ---
KOFI_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
JOIN_FORM_ACCESS = os.getenv("JOIN_FORM_ACCESS", "admin")

# ====================================================================
# NEW: STARTUP SANITY CHECKS
# This prevents the app from running without critical secrets.
# ====================================================================
if not app.config['SECRET_KEY']:
    raise RuntimeError("FATAL: FLASK_SECRET_KEY is not set in the environment.")
if not KOFI_TOKEN:
    raise RuntimeError("FATAL: KOFI_VERIFICATION_TOKEN is not set in the environment.")
if JOIN_FORM_ACCESS == "admin" and not ADMIN_API_TOKEN:
    raise RuntimeError("FATAL: JOIN_FORM_ACCESS is 'admin' but ADMIN_API_TOKEN is not set.")

# ====================================================================
# INTERNAL JOIN FORM
# ====================================================================

def check_admin_access(access_mode, required_token):
    """Helper function to check for admin access."""
    if access_mode == "admin":
        token = request.form.get('admin_token') or request.args.get('token')
        if not token or token != required_token:
            abort(403)

# ====================================================================
# API ROUTES
# ====================================================================

@app.route('/join', methods=['GET', 'POST'])
def join_form():
    """
    Renders a form and handles submission by internally calling the /webhook
    endpoint logic using Flask's test client for robustness.
    """
    check_admin_access(JOIN_FORM_ACCESS, ADMIN_API_TOKEN)

    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')

        if not email or not name:
            flash('Both name and email are required.', 'error')
            return redirect(url_for('join_form'))

        fake_payload = {
            "verification_token": KOFI_TOKEN,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "Subscription",
            "from_name": name,
            "message": "Manual join from internal form.",
            "amount": "3.00",
            "url": "#",
            "email": email,
            "currency": "USD",
            "is_subscription_payment": True,
            "is_first_subscription_payment": True,
            "kofi_transaction_id": f"form_generated_{str(uuid.uuid4())}",
            "tier_name": "lover",
        }

        try:
            # --- NEW: Use Flask's test_client for a robust internal call ---
            # This avoids network issues, redirects, and reverse proxy problems.
            with app.test_client() as client:
                logging.info(f"Internal form: dispatching fake event to /webhook for {email}")
                # We simulate the exact data format Ko-fi sends
                response = client.post('/webhook', data={'data': json.dumps(fake_payload)})

                # Check the status code from our own /webhook endpoint
                if response.status_code != 200:
                    # If our webhook logic failed, raise an error to be caught below
                    raise Exception(f"Internal webhook call failed with status {response.status_code}. Response: {response.get_data(as_text=True)}")

            # --- UPDATED SUCCESS MESSAGE ---
            flash(f"Success! Guardian '{name}' has been added. Please check your email for a welcome message.", 'success')

        except Exception as e:
            logging.error(f"Internal form: failed to process event for {email}. Error: {e}")
            # --- UPDATED ERROR MESSAGE ---
            flash("An error occurred while adding the guardian. The event could not be processed. Please check the server logs for details.", 'error')

        redirect_url = url_for('join_form', token=request.form.get('admin_token'))
        return redirect(redirect_url)

    return render_template('join.html', admin_token=request.args.get('token'))


@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    """Handles all Ko-fi webhooks."""
    if 'data' not in request.form:
        return jsonify({"error": "Malformed request, missing 'data' form field."}), 400

    try:
        data = json.loads(request.form['data'])
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in 'data' field."}), 400

    if data.get("verification_token") != KOFI_TOKEN:
        abort(403)
        
    # --- Step 1: Log EVERY valid event first ---
    # This now safely handles retries thanks to "INSERT OR IGNORE" in services.py
    services.log_kofi_event(data)

    # --- Step 2: Check if this is a membership-related payment ---
    # This is the crucial new logic. We only care if it's a subscription
    # payment AND it is tied to a specific membership tier.
    if (data.get("type") == "Subscription" and
        data.get("is_subscription_payment") is True and
        data.get("tier_name") is not None):
        
        logging.info(f"Processing MEMBERSHIP payment for tier '{data.get('tier_name')}' from {data.get('email')}")
        services.process_subscription_payment(data)
    else:
        # This will now correctly ignore simple Donations and non-tiered Subscriptions.
        logging.info(f"Ignoring non-membership event (type: '{data.get('type')}', tier: {data.get('tier_name')}). No action taken.")

    return jsonify({"message": "Webhook received successfully."}), 200


@app.route('/admin/housekeeping', methods=['POST'])
def housekeeping_route():
    """Protected admin route to clean up lapsed subscriptions."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or malformed."}), 401
    
    token = auth_header.split(' ')[1]
    if not ADMIN_API_TOKEN or token != ADMIN_API_TOKEN:
        return jsonify({"error": "Invalid or missing admin token."}), 403

    result = services.perform_housekeeping()
    return jsonify(result), 200


@app.route('/suggest', methods=['POST'])
def create_suggestion():
    """
    Public endpoint for users to suggest a new film.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON."}), 415

    data = request.get_json()
    email = data.get('email')
    title = data.get('title')

    if not email or not title:
        return jsonify({"error": "The 'email' and 'title' fields are required."}), 400
    
    notes = data.get('notes')

    try:
        new_suggestion = services.add_suggestion(email, title, notes)
        return jsonify({"message": "Suggestion received successfully.", "suggestion": new_suggestion}), 201
    except Exception as e:
        logging.error(f"Could not add suggestion: {e}")
        return jsonify({"error": "An internal error occurred."}), 500


@app.route('/auth')
def authenticate_guardian():
    """
    Validates a token and returns the guardian's core profile.
    """
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "API token is required."}), 401
    
    # Use the new, simpler service function
    guardian_profile = services.get_guardian_profile_by_token(token)
    
    if not guardian_profile:
        return jsonify({"error": "Invalid API token."}), 401
        
    return jsonify(guardian_profile), 200


@app.route('/magnet/<int:film_id>')
def get_magnet(film_id):
    """
    Provides the magnet link for a film if the user provides a valid token.
    """
    token = request.args.get('TOKEN')
    if not token:
        return jsonify({"error": "API token is required."}), 401

    guardian = services.get_guardian_by_token(token)
    if not guardian:
        return jsonify({"error": "Invalid API token."}), 401

    magnet_link = services.get_film_magnet(film_id)
    if not magnet_link:
        return jsonify({"error": "Film not found or has no magnet link."}), 404
        
    return jsonify({"film_id": film_id, "magnet": magnet_link})


@app.route('/adopt/<int:film_id>', methods=['POST'])
def adopt_film_route(film_id):
    """
    Allows a guardian to adopt a film.
    """
    token = request.args.get('TOKEN')
    if not token:
        return jsonify({"error": "API token is required."}), 401
    
    guardian = services.get_guardian_by_token(token)
    if not guardian:
        return jsonify({"error": "Invalid API token."}), 401

    response_data, status_code = services.adopt_film(guardian, film_id)
    return jsonify(response_data), status_code


@app.route('/db/public')
def download_public_db():
    """
    Publicly accessible route to download the latest generated public database.
    """
    directory = os.path.dirname(os.path.abspath(__file__))
    filename = "public.db"
    
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "Public database file not found. Please run the publish process first."}), 404


@app.route('/admin/publish', methods=['POST'])
def publish_database():
    """
    Protected route to generate and publish the sanitized public database.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or malformed."}), 401
        
    token = auth_header.split(' ')[1]
    if not ADMIN_API_TOKEN or token != ADMIN_API_TOKEN:
        return jsonify({"error": "Invalid or missing admin token."}), 403

    main_db_path = current_app.config['DATABASE']
    result = services.generate_public_database(main_db_path, "public.db")

    if result['status'] == 'success':
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@app.route('/db/public.sha256')
def get_public_db_checksum():
    """
    Publicly accessible SHA256 checksum for the public.db file.
    """
    sha256_path = os.path.join(os.path.dirname(__file__), 'public.db.sha256')

    if not os.path.exists(sha256_path):
        return jsonify({"error": "Checksum file not found."}), 404

    with open(sha256_path, "r") as f:
        checksum = f.read().strip()
    return checksum + "\n"



@app.route('/admin/upload-poster', methods=['POST'])
def upload_poster_route():
    """
    Protected admin route to upload a new film poster.
    Expects a multipart/form-data request with:
    - A 'poster' file (JPEG, < 1MB, ~2:3 ratio)
    - A 'film_slug' text field (e.g., 'blade-runner-2049')
    """
    # 1. --- Authentication ---
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or malformed."}), 401
    
    token = auth_header.split(' ')[1]
    if not ADMIN_API_TOKEN or token != ADMIN_API_TOKEN:
        return jsonify({"error": "Invalid or missing admin token."}), 403

    # 2. --- Input Validation ---
    if 'poster' not in request.files:
        return jsonify({"error": "Missing 'poster' file in the request."}), 400
    
    file = request.files['poster']

    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    # 3. --- Process and Save ---
    # Delegate all the hard work to the service layer
    result = utils.process_and_save_poster(file)

    # 4. --- Respond to Client ---
    if result['success']:
        # HTTP 201 Created is appropriate for a successful resource creation
        return jsonify({
            "message": "Poster uploaded and processed successfully.",
            "url": result['url']
        }), 201
    else:
        return jsonify({"error": result['error']}), 400


@app.route('/health')
def health_check():
    """
    A simple health check endpoint that the test script can hit.
    """
    return jsonify({"status": "ok"}), 200

# if __name__ == '__main__':
#    app.run(debug=False, port=5050)
