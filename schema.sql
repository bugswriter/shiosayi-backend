CREATE TABLE guardians (
    id TEXT PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    joined_at DATETIME NOT NULL,
    last_paid_at DATETIME
);

CREATE TABLE films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    plot TEXT,
    poster_url TEXT,
    region TEXT,
    guardian_id TEXT,
    status TEXT CHECK (status IN ('orphan', 'adopted')) NOT NULL DEFAULT 'orphan',
    magnet TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    title TEXT NOT NULL,
    notes TEXT,
    status TEXT CHECK (status IN ('pending', 'added', 'ignored')) DEFAULT 'pending',
    suggested_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE kofi_events (
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