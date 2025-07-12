# app.py
import os
import logging
# Make sure send_from_directory and current_app are imported from flask
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
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN") # Load Admin token

# --- All your routes below this line are unchanged, I'm just showing the import fix ---

@app.route('/health')
def health_check():
    """A simple health check endpoint that the test script can hit."""
    return jsonify({"status": "ok"}), 200

@app.route('/admin/publish', methods=['POST'])
def publish_database():
    """
    Protected route to generate and publish the sanitized public database.
    Requires admin token in the 'Authorization' header.
    e.g., Authorization: Bearer shio_admin_...
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or malformed."}), 401
        
    token = auth_header.split(' ')[1]
    if not ADMIN_API_TOKEN or token != ADMIN_API_TOKEN:
        return jsonify({"error": "Invalid or missing admin token."}), 403

    # This line will now work because 'current_app' is imported
    main_db_path = current_app.config['DATABASE']
    result = services.generate_public_database(main_db_path, "public.db")

    if result['status'] == 'success':
        return jsonify(result), 200
    else:
        return jsonify(result), 500


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


@app.route('/auth')
def authenticate_guardian():
    """
    Validates a token and returns the guardian's profile and adopted films.
    e.g., /auth?token=shio_xxxxxxxx
    """
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "API token is required."}), 401
    
    guardian_details = services.authenticate_and_get_details(token)
    
    if not guardian_details:
        return jsonify({"error": "Invalid API token."}), 401
        
    return jsonify(guardian_details), 200


@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    """
    Handles incoming webhooks from Ko-fi.
    """
    if not request.is_json:
        return jsonify({"error": "Unsupported Media Type, expecting application/json"}), 415

    data = request.get_json()

    # 1. Verify the request is from Ko-fi
    if data.get("verification_token") != KOFI_TOKEN:
        logging.warning("Webhook received with invalid verification token.")
        abort(403) # Forbidden

    # 2. Log every event for auditing
    services.log_kofi_event(data)

    # 3. Process only new subscriptions
    if (data.get("type") == "Subscription" and 
        data.get("is_first_subscription_payment") is True):
        
        logging.info(f"Processing new subscription for {data.get('email')}")
        services.process_new_subscription(data)
    else:
        logging.info(f"Ignoring Ko-fi event of type '{data.get('type')}'")

    return jsonify({"message": "Webhook received successfully."}), 200


@app.route('/magnet/<int:film_id>')
def get_magnet(film_id):
    """
    Provides the magnet link for a film if the user provides a valid token.
    e.g., /magnet/1?TOKEN=shio_xxxxxxxx
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
    e.g., POST /adopt/1?TOKEN=shio_xxxxxxxx
    """
    token = request.args.get('TOKEN')
    if not token:
        return jsonify({"error": "API token is required."}), 401
    
    guardian = services.get_guardian_by_token(token)
    if not guardian:
        return jsonify({"error": "Invalid API token."}), 401

    # The service function returns a tuple: (response_dict, status_code)
    response_data, status_code = services.adopt_film(guardian, film_id)

    return jsonify(response_data), status_code

if __name__ == '__main__':
    app.run(debug=False, port=5050)
