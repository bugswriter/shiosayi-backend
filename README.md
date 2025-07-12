# Shiosayi Backend

This is the Flask-based backend for the Shiosayi project. It manages a database of films, guardians (supporters), and suggestions, and handles interactions with external services like Ko-fi and Resend for email.

## Features

-   **Guardian Management**: Automatically creates "Guardian" accounts for new Ko-fi subscribers.
-   **Tier-Based Permissions**: Guardians have different abilities based on their subscription tier (`lover`, `keeper`, `savior`).
-   **Film Adoption**: Guardians can "adopt" orphan films, becoming their official keeper.
-   **Ko-fi Webhook Integration**: Listens for webhooks from Ko-fi to process new subscriptions.
-   **Film Suggestions**: A public API endpoint for anyone to suggest new films.
-   **Secure API**: Access to protected resources is controlled via unique API tokens.
-   **Public Database Publishing**: An admin-only route to generate and publish a sanitized, public-facing version of the database for frontend clients.

## Prerequisites

-   Python 3.10+
-   `pip` and `venv` (usually included with Python)
-   `sqlite3` command-line tool (for seeding the database)
-   `curl` and `jq` (for running the test script)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd shiosayi-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv env
    source env/bin/activate
    # On Windows, use: env\Scripts\activate
    ```

3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The application is configured using a `.env` file in the root directory. Create this file and add the following variables.

```ini
# .env

# Ko-fi webhook verification token
KOFI_VERIFICATION_TOKEN="your_kofi_verification_token_here"

# Resend API key for sending emails
RESEND_API_KEY="re_your_resend_api_key_here"

# Filename for the SQLite database
DATABASE_FILENAME="shiosayi.db"

# Admin token for triggering privileged actions
ADMIN_API_TOKEN="shio_admin_some_very_secret_token"

# Set to "true" to disable sending emails, useful for testing
TEST_MODE="true"
```

## Database Setup

1.  **Initialize the Database Schema:**
    This command creates the database file (e.g., `shiosayi.db`) and all the necessary tables.
    ```bash
    flask --app app init-db
    ```

2.  **Seed the Database with Dummy Data (Optional):**
    The `seed.sql` file contains sample data for guardians and films to get you started.
    ```bash
    sqlite3 shiosayi.db < seed.sql
    ```

## Running the Application

To run the local development server:

```bash
# Set TEST_MODE=true to prevent sending real emails during development
export TEST_MODE=true

# Run the Flask development server
flask --app app run --port 5001
```

The application will be available at `http://127.0.0.1:5001`.

## API Endpoints

| Method | Endpoint                    | Authentication | Description                                             |
| :----- | :-------------------------- | :------------- | :------------------------------------------------------ |
| `POST` | `/suggest`                  | Public         | Suggest a new film to be added.                         |
| `POST` | `/webhook`                  | Ko-fi Token    | Listens for webhooks from Ko-fi (for internal use).     |
| `GET`  | `/auth`                     | Guardian Token | Get a guardian's profile and their adopted films.       |
| `GET`  | `/magnet/<film_id>`         | Guardian Token | Get the magnet link for a specific film.                |
| `POST` | `/adopt/<film_id>`          | Guardian Token | Adopt an orphan or abandoned film.                      |
| `GET`  | `/db/public`                | Public         | Download the sanitized, public version of the database. |
| `POST` | `/admin/publish`            | Admin Token    | **[ADMIN]** Generate and publish the public database.     |
| `GET`  | `/health`                   | Public         | Health check endpoint for monitoring.                   |

### Authentication Types

-   **Public**: No authentication required.
-   **Guardian Token**: Requires `?TOKEN=<guardian_api_token>` in the URL query string.
-   **Admin Token**: Requires an `Authorization: Bearer <admin_api_token>` header.
-   **Ko-fi Token**: Validated internally from the webhook payload.

## Running Tests

A test script (`test.sh`) is provided to verify the core API functionality. It requires the server to be running.

1.  **Terminal 1: Start the Server**
    ```bash
    export TEST_MODE=true
    flask --app app run --port 5001
    ```

2.  **Terminal 2: Run the Test Script**
    ```bash
    # Make sure the script is executable
    chmod +x test.sh

    # Run the tests
    ./test.sh
    ```
