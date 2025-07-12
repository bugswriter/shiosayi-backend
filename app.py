# app.py

import os
import logging
import json  # <-- Import the json library
from flask import Flask, request, jsonify, abort, send_from_directory, current_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import logic from service layer and db functions
import services
import database

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Load config from .env, with a fallback
app.config['DATABASE'] = os.getenv("DATABASE_FILENAME", "shiosayi.db")

# Register database commands (init-db)
database.init_app(app)

# Load secrets from environment
KOFI_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")


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
        
    services.log_kofi_event(data)

    # --- SIMPLIFIED AND CORRECTED LOGIC ---
    if data.get("type") == "Subscription" and data.get("is_subscription_payment") is True:
        logging.info(f"Processing subscription payment for {data.get('email')}")
        services.process_subscription_payment(data)
    else:
        logging.info(f"Ignoring non-subscription Ko-fi event of type '{data.get('type')}'")

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


@app.route('/health')
def health_check():
    """
    A simple health check endpoint that the test script can hit.
    """
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(debug=False, port=5050)
