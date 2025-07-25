import os
import logging
import json
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, abort, render_template, flash, redirect, url_for, current_app, send_from_directory
from dotenv import load_dotenv
import services
import database
import utils

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

app.config['DATABASE'] = os.getenv("DATABASE_FILENAME", "shiosayi.db")
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
database.init_app(app)

KOFI_TOKEN = os.getenv("KOFI_VERIFICATION_TOKEN")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
JOIN_FORM_ACCESS = os.getenv("JOIN_FORM_ACCESS", "admin")
CDN_STORAGE_PATH = os.getenv("CDN_STORAGE_PATH")

if not app.config['SECRET_KEY']:
    raise RuntimeError("FATAL: FLASK_SECRET_KEY is not set in the environment.")
if not KOFI_TOKEN:
    raise RuntimeError("FATAL: KOFI_VERIFICATION_TOKEN is not set in the environment.")
if JOIN_FORM_ACCESS == "admin" and not ADMIN_API_TOKEN:
    raise RuntimeError("FATAL: JOIN_FORM_ACCESS is 'admin' but ADMIN_API_TOKEN is not set.")

def check_admin_access(access_mode, required_token):
    if access_mode == "admin":
        token = request.form.get('admin_token') or request.args.get('token')
        if not token or token != required_token:
            abort(403)

@app.route('/join', methods=['GET', 'POST'])
def join_form():
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
            with app.test_client() as client:
                logging.info(f"Internal form: dispatching fake event to /webhook for {email}")
                response = client.post('/webhook', data={'data': json.dumps(fake_payload)})
                if response.status_code != 200:
                    raise Exception(f"Internal webhook call failed with status {response.status_code}. Response: {response.get_data(as_text=True)}")

            flash(f"Success! Guardian '{name}' has been added. Please check your email for a welcome message.", 'success')
        except Exception as e:
            logging.error(f"Internal form: failed to process event for {email}. Error: {e}")
            flash("An error occurred while adding the guardian. The event could not be processed. Please check the server logs for details.", 'error')

        redirect_url = url_for('join_form', token=request.form.get('admin_token'))
        return redirect(redirect_url)

    return render_template('join.html', admin_token=request.args.get('token'))

@app.route('/webhook', methods=['POST'])
def kofi_webhook():
    if 'data' not in request.form:
        return jsonify({"error": "Malformed request, missing 'data' form field."}), 400

    try:
        data = json.loads(request.form['data'])
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in 'data' field."}), 400

    if data.get("verification_token") != KOFI_TOKEN:
        abort(403)

    services.log_kofi_event(data)

    if (data.get("type") == "Subscription" and
        data.get("is_subscription_payment") is True and
        data.get("tier_name") is not None):
        logging.info(f"Processing MEMBERSHIP payment for tier '{data.get('tier_name')}' from {data.get('email')}")
        services.process_subscription_payment(data)
    else:
        logging.info(f"Ignoring non-membership event (type: '{data.get('type')}', tier: {data.get('tier_name')}). No action taken.")

    return jsonify({"message": "Webhook received successfully."}), 200

@app.route('/admin/housekeeping', methods=['POST'])
def housekeeping_route():
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
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "API token is required."}), 401
    
    guardian_profile = services.get_guardian_profile_by_token(token)
    
    if not guardian_profile:
        return jsonify({"error": "Invalid API token."}), 401
        
    return jsonify(guardian_profile), 200

@app.route('/magnet/<int:film_id>')
def get_magnet(film_id):
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
    directory = os.path.join(CDN_STORAGE_PATH, "db")
    filename = "public.db"
    
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "Public database file not found. Please run the publish process first."}), 404

@app.route('/admin/publish', methods=['POST'])
def publish_database():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or malformed."}), 401
        
    token = auth_header.split(' ')[1]
    if not ADMIN_API_TOKEN or token != ADMIN_API_TOKEN:
        return jsonify({"error": "Invalid or missing admin token."}), 403

    main_db_path = current_app.config['DATABASE']
    
    db_dir = os.path.join(CDN_STORAGE_PATH, "db")
    public_db_full_path = os.path.join(db_dir, "public.db")
    
    os.makedirs(db_dir, exist_ok=True)
    
    result = services.generate_public_database(main_db_path, public_db_full_path)

    if result['status'] == 'success':
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/db/public.sha256')
def get_public_db_checksum():
    sha256_path = os.path.join(CDN_STORAGE_PATH, 'db', 'public.db.sha256')

    if not os.path.exists(sha256_path):
        return jsonify({"error": "Checksum file not found."}), 404

    with open(sha256_path, "r") as f:
        checksum = f.read().strip()
    return f"{checksum}\n"

@app.route('/admin/upload-poster', methods=['POST'])
def upload_poster_route():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or malformed."}), 401
    
    token = auth_header.split(' ')[1]
    if not ADMIN_API_TOKEN or token != ADMIN_API_TOKEN:
        return jsonify({"error": "Invalid or missing admin token."}), 403

    if 'poster' not in request.files:
        return jsonify({"error": "Missing 'poster' file in the request."}), 400
    
    file = request.files['poster']

    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    result = utils.process_and_save_poster(file)

    if result['success']:
        return jsonify({
            "message": "Poster uploaded and processed successfully.",
            "url": result['url']
        }), 201
    else:
        return jsonify({"error": result['error']}), 400

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"}), 200