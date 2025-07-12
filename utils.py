# utils.py
import secrets
import string

def generate_api_token(prefix="shio", length=32):
    """Generates a secure, random API token."""
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}_{token}"

def generate_guardian_id(db):
    """Generates a new sequential guardian ID (e.g., g001, g002)."""
    cursor = db.execute("SELECT id FROM guardians ORDER BY id DESC LIMIT 1")
    last_guardian = cursor.fetchone()
    
    if last_guardian is None:
        return "g001"
        
    last_id_str = last_guardian['id']
    # Assumes format 'g' + number
    last_num = int(last_id_str[1:])
    new_num = last_num + 1
    return f"g{new_num:03d}"
