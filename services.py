# services.py

import os
import logging
import sqlite3
from datetime import datetime

from database import get_db
from utils import generate_api_token, generate_guardian_id
from mail import EmailService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tier definitions for adoption limits
TIER_MAP = {
    "lover": "lover",
    "keeper": "keeper",
    "savior": "savior"
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
    - Copies the 'guardians' table but EXCLUDES the 'email' and 'token' columns.
    - Copies the 'films' table but EXCLUDES the 'magnet' column.

    Args:
        main_db_path (str): The path to the main private database.
        public_db_path (str): The filename for the public database to be created.

    Returns:
        dict: A result dictionary indicating success or failure.
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
        main_db = sqlite3.connect(f"file:{main_db_path}?mode=ro", uri=True)
        main_db.row_factory = sqlite3.Row
        public_db = sqlite3.connect(public_db_path)
        main_cursor = main_db.cursor()
        public_cursor = public_db.cursor()

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
        main_cursor.execute("SELECT id, title, year, plot, poster_url, region, guardian_id, status, updated_at FROM films")
        films_to_copy = main_cursor.fetchall()
        if films_to_copy:
            public_cursor.executemany(
                """INSERT INTO films (id, title, year, plot, poster_url, region, guardian_id, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                films_to_copy
            )
        
        public_db.commit()
        logging.info(f"Successfully created public database '{public_db_path}'.")
        return {
            "status": "success",
            "message": f"Public database '{public_db_path}' created successfully.",
            "guardians_published": len(guardians_to_copy),
            "films_published": len(films_to_copy)
        }

    except sqlite3.Error as e:
        logging.error(f"An SQLite error occurred during public database generation: {e}")
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
