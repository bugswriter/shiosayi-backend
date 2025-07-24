# app.py
import os
import logging
import json
import requests
from flask import Flask, request, jsonify, abort, send_from_directory, current_app
from dotenv import load_dotenv

load_dotenv()
import services
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

app.config['DATABASE'] = os.getenv("DATABASE_FILENAME", "shiosayi.db")
database.init_app(app)

KOFI_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
JOIN_FORM_ACCESS = os.getenv("JOIN_FORM_ACCESS")

def check_admin_access():
    if JOIN_FORM_ACCESS == "admin":
        token = request.form.get('admin_token') or request.args.get('token')
        if token != ADMIN_API_TOKEN:
            abort(403) # Forbidden

# ====================================================================
# API ROUTES
# ====================================================================

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


@app.route('/join', methods=['GET', 'POST'])
def join_form():
    """
    Renders a form and handles its submission by making a server-to-server
    request to the /webhook endpoint, simulating a real Ko-fi event.
    Access is controlled by the JOIN_FORM_ACCESS environment variable.
    """
    check_admin_access() # Protect the route if in 'admin' mode

    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')

        if not email or not name:
            flash('Both name and email are required.', 'error')
            return redirect(url_for('join_form'))

        fake_payload = {
            "verification_token": KOFI_TOKEN, # This is the "key" to our own webhook
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "Subscription",
            "is_public": False,
            "from_name": name,
            "message": "Manual join from internal form.",
            "amount": "3.00",
            "url": "#",
            "email": email,
            "currency": "USD",
            "is_subscription_payment": True,
            "is_first_subscription_payment": True,
            # This marker helps you identify form-generated users in your DB
            "kofi_transaction_id": f"form_generated_{str(uuid.uuid4())}",
            "tier_name": "lover", # Hardcoded to 'lover'
            "shipping": None
        }

        try:
            # Step 2: Make the server-to-server POST request to the /webhook.
            # This re-uses the exact same logic as a real Ko-fi event.
            webhook_url = url_for('kofi_webhook', _external=True)
            # Ko-fi sends data as a form field containing a JSON string.
            form_data = {'data': json.dumps(fake_payload)}
            
            logging.info(f"Internal form: sending fake event to {webhook_url} for {email}")
            response = requests.post(webhook_url, data=form_data, timeout=10)

            # Step 3: Check the response from our own webhook.
            response.raise_for_status() # Raises an exception for 4xx or 5xx status codes

            flash(f"Success! Guardian '{name}' ({email}) has been added.", 'success')

        except requests.exceptions.RequestException as e:
            logging.error(f"Internal form: failed to call /webhook endpoint: {e}")
            flash(f"An error occurred: {e}", 'error')

        redirect_url = url_for('join_form', token=request.form.get('admin_token'))
        return redirect(redirect_url)

    return render_template('join.html', admin_token=request.args.get('token'))


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
    Validates a token and returns the guardian's profile and adopted films.
    """
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "API token is required."}), 401
    
    guardian_details = services.authenticate_and_get_details(token)
    
    if not guardian_details:
        return jsonify({"error": "Invalid API token."}), 401
        
    return jsonify(guardian_details), 200


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


@app.route('/health')
def health_check():
    """
    A simple health check endpoint that the test script can hit.
    """
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(debug=False, port=5050)
