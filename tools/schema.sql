-- =============================
-- Table: guardians
-- =============================
CREATE TABLE guardians (
    id TEXT PRIMARY KEY,                -- e.g., g001
    name TEXT,                          -- optional display name
    email TEXT UNIQUE NOT NULL,         -- for contact + matching
    tier TEXT NOT NULL,                 -- lover, keeper, savior
    token TEXT UNIQUE NOT NULL,         -- access token / API key
    joined_at DATETIME NOT NULL         -- date of registration
);

-- =============================
-- Table: films
-- =============================
CREATE TABLE films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    plot TEXT,
    poster_url TEXT,
    region TEXT,
    guardian_id TEXT,                   -- links to guardians.id (nullable)
    status TEXT CHECK (status IN ('orphan', 'adopted', 'abandoned')) NOT NULL DEFAULT 'orphan',
    magnet TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================
-- Table: suggestions
-- =============================
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,               -- person suggesting
    title TEXT NOT NULL,               -- suggested film
    notes TEXT,                        -- optional message
    status TEXT CHECK (status IN ('pending', 'added', 'ignored')) DEFAULT 'pending',
    suggested_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================
-- Table: kofi_events
-- =============================
CREATE TABLE kofi_events (
    id TEXT PRIMARY KEY,                       -- message_id from Ko-fi
    timestamp DATETIME NOT NULL,               -- time of event
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
    raw_payload TEXT                            -- optional: store full JSON
);
