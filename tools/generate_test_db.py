
import sqlite3
from datetime import datetime, timedelta
import random
import uuid

# Create SQLite DB
conn = sqlite3.connect("./shiosayi_test.db")
c = conn.cursor()

# Create tables
c.executescript("""
CREATE TABLE IF NOT EXISTS guardians (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    tier INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    joined_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    plot TEXT,
    poster_url TEXT,
    region TEXT,
    guardian_id TEXT,
    status TEXT CHECK (status IN ('orphan', 'adopted', 'abandoned')) NOT NULL DEFAULT 'orphan',
    magnet TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    title TEXT NOT NULL,
    notes TEXT,
    status TEXT CHECK (status IN ('pending', 'added', 'ignored')) DEFAULT 'pending',
    suggested_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kofi_events (
    id TEXT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    type TEXT CHECK (type IN ('Donation', 'Subscription')) NOT NULL,
    is_public BOOLEAN,
    from_name TEXT,
    email TEXT NOT NULL,
    message TEXT,
    amount REAL,
    currency TEXT,
    url TEXT,
    is_subscription_payment BOOLEAN,
    is_first_subscription_payment BOOLEAN,
    tier_name TEXT,
    kofi_transaction_id TEXT,
    raw_payload TEXT
);
""")

# Sample guardians
for i in range(1, 6):
    guardian_id = f"g{i:03d}"
    name = f"Guardian{i}"
    email = f"guardian{i}@example.com"
    tier = random.choice([1, 5, 10])
    token = str(uuid.uuid4())
    joined_at = datetime.now() - timedelta(days=random.randint(0, 60))
    c.execute("INSERT INTO guardians VALUES (?, ?, ?, ?, ?, ?)",
              (guardian_id, name, email, tier, token, joined_at.isoformat()))

# Sample films
statuses = ['orphan', 'adopted', 'abandoned']
for i in range(1, 11):
    title = f"Rare Film {i}"
    year = random.randint(1950, 2000)
    plot = f"Plot of film {i}."
    poster_url = f"https://example.com/poster{i}.jpg"
    region = random.choice(['Japan', 'India', 'France', 'Iran'])
    guardian_id = f"g{random.randint(1, 5):03d}" if i % 3 != 0 else None
    status = 'adopted' if guardian_id else 'orphan'
    magnet = f"magnet:?xt=urn:btih:{uuid.uuid4().hex}&dn=Rare+Film+{i}"
    updated_at = datetime.now().isoformat()
    c.execute("""INSERT INTO films (title, year, plot, poster_url, region, guardian_id, status, magnet, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (title, year, plot, poster_url, region, guardian_id, status, magnet, updated_at))

# Sample suggestions
for i in range(1, 6):
    email = f"user{i}@mail.com"
    title = f"Suggested Film {i}"
    notes = f"This is a suggestion for film {i}"
    status = random.choice(['pending', 'added', 'ignored'])
    suggested_at = datetime.now() - timedelta(days=random.randint(1, 20))
    c.execute("INSERT INTO suggestions (email, title, notes, status, suggested_at) VALUES (?, ?, ?, ?, ?)",
              (email, title, notes, status, suggested_at.isoformat()))

# Sample kofi events
for i in range(1, 6):
    message_id = str(uuid.uuid4())
    timestamp = datetime.now() - timedelta(days=random.randint(0, 30))
    type_ = random.choice(['Donation', 'Subscription'])
    is_public = True
    from_name = f"Donor{i}"
    email = f"guardian{i}@example.com"
    message = f"Support message {i}"
    amount = random.choice([1.00, 5.00, 10.00])
    currency = "USD"
    url = "https://ko-fi.com/tx/123456"
    is_subscription = type_ == 'Subscription'
    is_first = bool(random.getrandbits(1))
    tier_name = "Bronze" if amount <= 5 else "Silver"
    kofi_tx_id = str(uuid.uuid4())
    raw_payload = "{}"
    c.execute("""INSERT INTO kofi_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (message_id, timestamp.isoformat(), type_, is_public, from_name, email, message, amount, currency, url,
               is_subscription, is_first, tier_name, kofi_tx_id, raw_payload))

conn.commit()
conn.close()
