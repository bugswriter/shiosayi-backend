# services.py
import os
import logging
import sqlite3
import csv
import hashlib
from datetime import datetime, timedelta

from database import get_db
from utils import generate_api_token, generate_guardian_id
from mail import EmailService
from flask import current_app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TIER_LIMITS = {'lover': 1, 'keeper': 5, 'savior': 10}
TIER_MAP = {"lover": "lover", "keeper": "keeper", "savior": "savior"}

def log_kofi_event(payload):
    """
    Logs the raw Ko-fi event to the database.
    Uses INSERT OR IGNORE to safely handle webhook retries.
    """
    db = get_db()
    # FIX: Use INSERT OR IGNORE to prevent UNIQUE constraint errors on retry
    db.execute(
        """
        INSERT OR IGNORE INTO kofi_events (id, timestamp, type, is_public, from_name, email, message,
        amount, currency, url, is_subscription_payment, is_first_subscription_payment,
        tier_name, kofi_transaction_id, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload['message_id'], payload['timestamp'], payload['type'],
            payload.get('is_public'), payload.get('from_name'), payload['email'],
            payload.get('message'), float(payload['amount']), payload.get('currency'),
            payload.get('url'), payload.get('is_subscription_payment'),
            payload.get('is_first_subscription_payment'), payload.get('tier_name'),
            payload.get('kofi_transaction_id'), str(payload)
        )
    )
    db.commit()
    logging.info(f"Logged (or ignored duplicate) Ko-fi event: {payload['message_id']}")


def process_subscription_payment(payload):
    """
    Handles a confirmed MEMBERSHIP payment.
    - Updates an existing guardian's payment date and handles tier upgrades.
    - Creates a new guardian if they don't exist.
    """
    email = payload.get('email')
    db = get_db()
    cursor = db.execute("SELECT id, tier, token FROM guardians WHERE email = ?", (email,))
    guardian = cursor.fetchone()
    
    email_service = EmailService()
    
    # FIX: Safely handle the tier_name, even though app.py filters for None
    kofi_tier_name = payload.get('tier_name')
    if kofi_tier_name:
        kofi_tier_name = kofi_tier_name.lower()
    app_tier = TIER_MAP.get(kofi_tier_name, 'lover')

    if guardian:
        # --- EXISTING GUARDIAN (RENEWAL OR UPGRADE) ---
        current_tier, guardian_id, guardian_token = guardian['tier'], guardian['id'], guardian['token']
        db.execute("UPDATE guardians SET last_paid_at = ?, tier = ? WHERE id = ?", (datetime.now(), app_tier, guardian_id))
        db.commit()

        if app_tier != current_tier:
            logging.info(f"Guardian {guardian_id} upgraded from '{current_tier}' to '{app_tier}'.")
            email_service.send_email(
                to_email=email, subject="Your Shiosayi Tier has been Upgraded!",
                template_name="guardian_welcome_email",
                template_data={
                    "title": f"Congratulations! You're now a {app_tier.capitalize()} Guardian!",
                    "user_name": payload.get('from_name'), "tier_name": app_tier, "api_key": guardian_token
                }
            )
        else:
            logging.info(f"Processed renewal for existing guardian {guardian_id}.")
            
    else:
        # --- NEW GUARDIAN ---
        logging.info(f"Creating new guardian for {email}.")
        _create_new_guardian(payload, app_tier, email_service)


def _create_new_guardian(payload, app_tier, email_service):
    """Internal function to create a new guardian and send the welcome email."""
    db = get_db()
    email, new_id, new_token = payload['email'], generate_guardian_id(db), generate_api_token()
    
    guardian_data = {
        'id': new_id, 'name': payload.get('from_name'), 'email': email, 'tier': app_tier,
        'token': new_token, 'joined_at': datetime.now(), 'last_paid_at': datetime.now()
    }
    db.execute(
        """
        INSERT INTO guardians (id, name, email, tier, token, joined_at, last_paid_at)
        VALUES (:id, :name, :email, :tier, :token, :joined_at, :last_paid_at)
        """, guardian_data
    )
    db.commit()
    logging.info(f"Created new guardian: {new_id} ({email}) with tier '{app_tier}'")

    email_service.send_email(
        to_email=email, subject="Welcome to the Shiosayi Community!",
        template_name="guardian_welcome_email",
        template_data={"user_name": guardian_data['name'], "tier_name": app_tier, "api_key": new_token}
    )


def perform_housekeeping(days_lapsed=35, archive_file="ex_guardians.csv"):
    """
    Finds guardians whose subscriptions have lapsed and cleans them up.
    This is the definitive way to handle cancellations.
    """
    db = get_db()
    cutoff_date = datetime.now() - timedelta(days=days_lapsed)
    logging.info(f"Housekeeping: Checking for guardians with no payment since {cutoff_date.strftime('%Y-%m-%d')}.")

    cursor = db.execute("SELECT * FROM guardians WHERE last_paid_at < ?", (cutoff_date,))
    lapsed_guardians = cursor.fetchall()

    if not lapsed_guardians:
        logging.info("Housekeeping: No lapsed guardians found.")
        return {"message": "No lapsed guardians to process."}

    logging.info(f"Housekeeping: Found {len(lapsed_guardians)} lapsed guardians to process.")
    
    archived_count, films_abandoned_count = 0, 0
    
    file_exists = os.path.isfile(archive_file)
    with open(archive_file, 'a', newline='') as csvfile:
        fieldnames = lapsed_guardians[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists: writer.writeheader()
        
        for guardian in lapsed_guardians:
            writer.writerow(dict(guardian))
            archived_count += 1
            
            update_cursor = db.execute(
                "UPDATE films SET status = 'abandoned', guardian_id = NULL WHERE guardian_id = ?", (guardian['id'],)
            )
            films_abandoned_count += update_cursor.rowcount

            db.execute("DELETE FROM guardians WHERE id = ?", (guardian['id'],))
    
    db.commit()
    logging.info(f"Housekeeping complete. Archived: {archived_count}, Films abandoned: {films_abandoned_count}.")
    
    return {
        "message": "Housekeeping process completed successfully.",
        "archived_guardians": archived_count, "films_abandoned": films_abandoned_count
    }


def log_kofi_event(payload):
    """Logs the raw Ko-fi event to the database for auditing."""
    db = get_db()
    db.execute(
        """
        INSERT INTO kofi_events (id, timestamp, type, is_public, from_name, email, message,
        amount, currency, url, is_subscription_payment, is_first_subscription_payment,
        tier_name, kofi_transaction_id, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload['message_id'],
            payload['timestamp'],
            payload['type'],
            payload.get('is_public'),
            payload.get('from_name'),
            payload['email'],
            payload.get('message'),
            float(payload['amount']),
            payload.get('currency'),
            payload.get('url'),
            payload.get('is_subscription_payment'),
            payload.get('is_first_subscription_payment'),
            payload.get('tier_name'),
            payload.get('kofi_transaction_id'),
            str(payload)
        )
    )
    db.commit()
    logging.info(f"Logged Ko-fi event: {payload['message_id']}")


def process_new_subscription(payload):
    """
    Processes a new subscription webhook. If the user is new, creates a guardian,
    generates an API key, and sends a welcome email.
    """
    db = get_db()
    email = payload['email']
    
    # Check if a guardian with this email already exists
    cursor = db.execute("SELECT id FROM guardians WHERE email = ?", (email,))
    existing_guardian = cursor.fetchone()

    if existing_guardian:
        logging.info(f"Guardian with email {email} already exists. No action taken.")
        return None # Indicate no new guardian was created

    # --- Create a new guardian ---
    new_id = generate_guardian_id(db)
    new_token = generate_api_token()
    kofi_tier_name = payload.get('tier_name')
    
    # Map Ko-fi tier name to our internal tier name, default to 'lover'
    app_tier = TIER_MAP.get(kofi_tier_name, 'lover')
    
    guardian_data = {
        'id': new_id,
        'name': payload.get('from_name'),
        'email': email,
        'tier': app_tier,
        'token': new_token,
        'joined_at': datetime.now()
    }

    db.execute(
        """
        INSERT INTO guardians (id, name, email, tier, token, joined_at)
        VALUES (:id, :name, :email, :tier, :token, :joined_at)
        """,
        guardian_data
    )
    db.commit()
    logging.info(f"Created new guardian: {new_id} ({email}) with tier '{app_tier}'")

    try:
        email_service = EmailService()
        email_service.send_email(
            to_email=email, # Pass the REAL user email
            subject="Welcome to Shiosayi! Here is your API Key",
            template_name="api_key_email",
            template_data={
                "user_name": guardian_data['name'],
                "api_key": guardian_data['token']
            }
        )
    except Exception as e:
        logging.error(f"Failed to trigger email service for {email}: {e}")

    return guardian_data


def get_guardian_by_token(token):
    """Fetches a guardian from the database by their API token."""
    db = get_db()
    cursor = db.execute("SELECT * FROM guardians WHERE token = ?", (token,))
    guardian = cursor.fetchone()
    return guardian # Returns a Row object or None


def get_film_magnet(film_id):
    """Fetches a film's magnet link."""
    db = get_db()
    cursor = db.execute("SELECT magnet FROM films WHERE id = ?", (film_id,))
    film = cursor.fetchone()
    return film['magnet'] if film and film['magnet'] else None


def adopt_film(guardian, film_id):
    """
    Logic for a guardian to adopt a film.
    Checks tier limits and film status.
    """
    db = get_db()
    guardian_id = guardian['id']
    guardian_tier = guardian['tier']

    # 1. Check film status
    cursor = db.execute("SELECT * FROM films WHERE id = ?", (film_id,))
    film = cursor.fetchone()

    if not film:
        return {"error": "Film not found."}, 404
    
    if film['status'] == 'adopted':
        if film['guardian_id'] == guardian_id:
            return {"message": "You have already adopted this film."}, 200
        else:
            return {"error": "This film is already adopted by another guardian."}, 409

    # 2. Check guardian's adoption limit
    limit = TIER_LIMITS.get(guardian_tier, 0)
    cursor = db.execute("SELECT COUNT(id) FROM films WHERE guardian_id = ? AND status = 'adopted'", (guardian_id,))
    current_adoptions = cursor.fetchone()[0]

    if current_adoptions >= limit:
        return {"error": f"Adoption limit reached. Your tier '{guardian_tier}' allows for {limit} adoptions."}, 403

    # 3. Adopt the film
    db.execute(
        "UPDATE films SET guardian_id = ?, status = 'adopted', updated_at = ? WHERE id = ?",
        (guardian_id, datetime.now(), film_id)
    )
    db.commit()
    logging.info(f"Guardian {guardian_id} adopted film {film_id}.")
    
    return {"message": "Film successfully adopted!", "film_title": film['title']}, 200


def authenticate_and_get_details(token):
    """
    Validates a token and returns guardian details along with their adopted films.
    """
    guardian = get_guardian_by_token(token)
    if not guardian:
        return None # Token is invalid or not found

    db = get_db()
    cursor = db.execute(
        "SELECT id, title, year, plot, poster_url, region FROM films WHERE guardian_id = ? AND status = 'adopted'",
        (guardian['id'],)
    )
    adopted_films_rows = cursor.fetchall()
    
    adopted_films = [dict(row) for row in adopted_films_rows]
    
    guardian_details = {
        "name": guardian['name'],
        "email": guardian['email'],
        "tier": guardian['tier'],
        "films": adopted_films
    }
    
    return guardian_details


def generate_public_database(main_db_path, public_db_path="public.db"):
    """
    Creates a public-facing, sanitized version of the database.

    - Backs up the old public DB with a timestamp if it exists.
    - Creates a new public DB file.
    - Copies the 'guardians' table (excluding sensitive fields).
    - Copies the 'films' table (excluding magnet link).
    - Generates SHA256 checksum file: public.db.sha256

    Args:
        main_db_path (str): Path to the main private database.
        public_db_path (str): Filename for the public database to create.

    Returns:
        dict: Result dictionary indicating success or failure.
    """
    if os.path.exists(public_db_path):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_path = f"{public_db_path}.{timestamp}.bak"
        try:
            os.rename(public_db_path, backup_path)
            logging.info(f"Backed up existing public database to {backup_path}")
        except OSError as e:
            logging.error(f"Failed to back up database: {e}")
            return {"status": "error", "message": f"Failed to back up database: {e}"}

    main_db = None
    public_db = None
    try:
        # Open main DB in read-only mode
        main_db = sqlite3.connect(f"file:{main_db_path}?mode=ro", uri=True)
        main_db.row_factory = sqlite3.Row
        public_db = sqlite3.connect(public_db_path)

        main_cursor = main_db.cursor()
        public_cursor = public_db.cursor()

        # === Guardians Table ===
        public_cursor.execute("""
        CREATE TABLE guardians (
            id TEXT PRIMARY KEY,
            name TEXT,
            tier TEXT NOT NULL,
            joined_at DATETIME NOT NULL
        );
        """)
        main_cursor.execute("SELECT id, name, tier, joined_at FROM guardians")
        guardians_to_copy = main_cursor.fetchall()
        if guardians_to_copy:
            public_cursor.executemany(
                "INSERT INTO guardians (id, name, tier, joined_at) VALUES (?, ?, ?, ?)",
                guardians_to_copy
            )

        # === Films Table ===
        public_cursor.execute("""
        CREATE TABLE films (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            year INTEGER,
            plot TEXT,
            poster_url TEXT,
            region TEXT,
            guardian_id TEXT,
            status TEXT CHECK (status IN ('orphan', 'adopted', 'abandoned')) NOT NULL,
            updated_at DATETIME
        );
        """)
        main_cursor.execute("""
            SELECT id, title, year, plot, poster_url, region, guardian_id, status, updated_at 
            FROM films
        """)
        films_to_copy = main_cursor.fetchall()
        if films_to_copy:
            public_cursor.executemany(
                """INSERT INTO films 
                   (id, title, year, plot, poster_url, region, guardian_id, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                films_to_copy
            )

        # Commit public DB
        public_db.commit()
        logging.info(f"Successfully created public database '{public_db_path}'.")

        # === SHA256 Checksum ===
        sha256_path = public_db_path + ".sha256"
        try:
            with open(public_db_path, "rb") as f:
                sha256 = hashlib.sha256(f.read()).hexdigest()
            with open(sha256_path, "w") as f:
                f.write(sha256 + "\n")
            logging.info(f"Checksum written to '{sha256_path}'")
        except Exception as e:
            logging.warning(f"Failed to generate SHA256 file: {e}")

        return {
            "status": "success",
            "message": f"Public database '{public_db_path}' created successfully.",
            "guardians_published": len(guardians_to_copy),
            "films_published": len(films_to_copy)
        }

    except sqlite3.Error as e:
        logging.error(f"SQLite error during public DB generation: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        if main_db:
            main_db.close()
        if public_db:
            public_db.close()


def add_suggestion(email, title, notes=None):
    """
    Inserts a new film suggestion into the database.

    Args:
        email (str): The email of the person suggesting the film.
        title (str): The title of the suggested film.
        notes (str, optional): Any additional notes from the suggester.

    Returns:
        dict: A dictionary representing the newly created suggestion row.
    """
    db = get_db()
    cursor = db.execute(
        "INSERT INTO suggestions (email, title, notes) VALUES (?, ?, ?)",
        (email, title, notes)
    )
    db.commit()
    
    new_suggestion_id = cursor.lastrowid
    
    # Fetch the newly created suggestion to return it in the API response
    new_suggestion_cursor = db.execute("SELECT * FROM suggestions WHERE id = ?", (new_suggestion_id,))
    created_suggestion = dict(new_suggestion_cursor.fetchone())
    
    logging.info(f"New suggestion added: ID {new_suggestion_id} for title '{title}' by {email}.")
    return created_suggestion
