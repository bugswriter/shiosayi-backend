# Shiosayi Backend

This is the Flask-based backend for the Shiosayi film preservation project. It manages a database of films and their guardians, handles Ko-fi webhooks for memberships, and provides a public API for client applications.

## Core Features

-   **Guardian Management**: Automatically handles new memberships and tier upgrades from Ko-fi.
-   **Tier-Based Permissions**: Guardians can adopt films based on their `lover`, `keeper`, or `savior` tier.
-   **Automated Housekeeping**: A robust system for managing lapsed subscriptions.
-   **Offline-First API**: Provides a downloadable public database for fast, efficient client applications.
-   **Secure Endpoints**: Protected actions are secured via Guardian and Admin API tokens.

---

## Quickstart

### 1. Prerequisites

-   Python 3.9+
-   `pip` and `venv`
-   `sqlite3` command-line tool

### 2. Installation

```bash
# Clone the repository
git clone <your-repository-url>
cd shiosayi-backend

# Create and activate a virtual environment
python -m venv env
source env/bin/activate
# On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the project root by copying `.env.example` (or creating it from scratch). Fill in the required values:

```ini
# .env
KOFI_VERIFICATION_TOKEN="your_kofi_verification_token"
RESEND_API_KEY="re_your_resend_api_key"
DATABASE_FILENAME="shiosayi.db"
ADMIN_API_TOKEN="a_strong_secret_token_for_admin_actions"
BASE_URL="http://127.0.0.1:5001"
TEST_MODE="true"
TEST_EMAIL_RECIPIENT="delivered@resend.dev"
```

### 4. Database Setup

```bash
# Create the database schema
flask --app app init-db

# (Optional) Seed the database with sample data
sqlite3 shiosayi.db < seed.sql
```

### 5. Running the Server

```bash
# Run the local development server
flask --app app run --port 5001
```

The application will be running at `http://127.0.0.1:5001`.

---

## Documentation

For detailed information on how to use the system, please refer to the documentation pages:

-   **[Public API Documentation](./api_docs.html)**: A guide for developers building client applications (desktop, CLI, etc.). It explains the offline-first approach and details all public endpoints.

-   **[Internal System Documentation](./internal_docs.html)**: A comprehensive guide for backend developers and system administrators. It covers the architecture, database schema, core logic, and administrative tasks.

## Testing

The project includes an interactive test suite to validate the entire user lifecycle.

1.  **Start the server** in one terminal (`flask --app app run`).
2.  **Run the test flow script** in a second terminal:
    ```bash
    python run_test_flow.py
    ```
    The script will guide you through each test case interactively.
