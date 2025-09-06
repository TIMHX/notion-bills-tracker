# Notion Bill Tracker

This project automates the process of tracking bills from your Gmail inbox and adding them to a Notion database. It uses the Google Gemini API to extract bill information from emails and the Notion API to manage your bill tracking.

## Features

-   **Gmail Integration**: Fetches unread emails from your Gmail inbox, specifically those from "Chase" with the label "大通银行明细".
-   **Gemini AI Extraction**: Utilizes Google Gemini (model `gemini-2.0-flash-lite`) to intelligently extract bill details:
    -   `merchant` (支出项目)
    -   `amount` (支出金额)
    -   `account_type` (支出类别 - e.g., "支票账户" for checking account or "信用卡" for credit card)
    -   `date` (覆写日期 - in YYYY-MM-DD format)
-   **Notion Database Management**: Adds extracted bill information to a specified Notion database with predefined properties.
-   **Automated Workflow**: Designed to run automatically via GitHub Actions every 6 hours, and can also be triggered manually.
-   **Configurable Logging**: Utilizes `logger_utils.py` for structured logging with configurable levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) via environment variables.
-   **Workflow Tracking**: Tracks the status of each workflow run in a dedicated Notion database, providing visibility into automation health.

## Project Structure

```
notion-bills-tracker/
├── .github/
│   └── workflows/
│       └── process-bills.yml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── gmail_client.py
│   ├── gemini_processor.py
│   ├── notion_client.py
│   ├── logger_utils.py
│   └── workflow_tracker.py
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/notion-bills-tracker.git
cd notion-bills-tracker
```

### 2. Set up a Python Virtual Environment with uv

This project uses `uv` for dependency management.

```bash
# Install uv if you haven't already
# pip install uv

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
uv sync
```

### 3. Google Cloud & Gmail API Setup

To use the Gmail API, you'll need to set up OAuth 2.0 credentials. This project uses a refresh token for non-interactive authentication, which is ideal for automated scripts.

1.  **Create a Google Cloud Project**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.
    *   Enable the **Gmail API** for your project.

2.  **Configure OAuth Consent Screen**:
    *   Go to "APIs & Services" > "OAuth consent screen".
    *   Choose "External" and create the consent screen.
    *   Provide an app name, user support email, and developer contact information.
    *   In the "Scopes" section, add the following scopes:
        *   `https://www.googleapis.com/auth/gmail.readonly`
        *   `https://www.googleapis.com/auth/gmail.modify`
    *   In the "Test users" section, add the Google account you'll be using to access Gmail.

3.  **Create OAuth 2.0 Credentials**:
    *   Go to "APIs & Services" > "Credentials".
    *   Click "Create Credentials" > "OAuth client ID".
    *   Select "Web application" as the application type.
    *   Under "Authorized redirect URIs", add `https://developers.google.com/oauthplayground`.
    *   Click "Create". You will get a **Client ID** and **Client Secret**.

4.  **Generate a Refresh Token**:
    *   Go to the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
    *   In the top right corner, click the gear icon ("OAuth 2.0 configuration").
    *   Check "Use your own OAuth credentials" and enter your **Client ID** and **Client Secret**.
    *   In the "Step 1: Select & authorize APIs" section, paste the following scopes and click "Authorize APIs":
        `https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify`
    *   Follow the prompts to grant access to your Google account.
    *   In "Step 2: Exchange authorization code for tokens", click "Exchange authorization code for tokens".
    *   You will receive a **Refresh token**. Copy this value.

### 4. Google Gemini API Key

1.  Go to the [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Create an API key.
3.  **Do NOT commit this key to Git.**

### 5. Notion Integration Token & Database ID

1.  Go to your [Notion Integrations page](https://www.notion.so/my-integrations).
2.  Click "New integration".
3.  Give it a name (e.g., "Bill Tracker Integration") and associate it with your workspace.
4.  Copy the "Internal Integration Token".
5.  Create a new Notion database for your bills. It should have the following properties (case-sensitive, using Chinese names as per implementation):
    -   `支出项目` (Title)
    -   `覆写日期` (Date)
    -   `支出金额` (Number)
    -   `支出类别` (Select - e.g., "信用卡", "支票账户")
6.  Share your Notion database with the integration you just created.
7.  Copy the Database ID from the URL of your Notion database. It's the part after `https://www.notion.so/` and before `?v=...`.

### 6. Environment Variables

Create a `.env` file in the root of your project with the following variables:

```
GMAIL_CLIENT_ID=YOUR_GMAIL_CLIENT_ID
GMAIL_CLIENT_SECRET=YOUR_GMAIL_CLIENT_SECRET
GMAIL_REFRESH_TOKEN=YOUR_GMAIL_REFRESH_TOKEN
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
NOTION_API_KEY=YOUR_NOTION_API_KEY
NOTION_DATABASE_ID=YOUR_NOTION_DATABASE_ID
NOTION_WORKFLOW_DATABASE_ID=YOUR_NOTION_WORKFLOW_DATABASE_ID
LOG_LEVEL=WARNING # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Replace the placeholder values with your actual credentials.

## Running Locally

```bash
python src/main.py
```

The script uses the refresh token to authenticate with the Gmail API, so no browser interaction is needed after the initial setup.

## GitHub Actions Setup

To run this project automatically on GitHub Actions, you need to set up repository secrets:

1.  Go to your GitHub repository settings.
2.  Navigate to "Secrets and variables" > "Actions".
3.  Add the following repository secrets:
    -   `GMAIL_CLIENT_ID`: Your Google Cloud OAuth Client ID.
    -   `GMAIL_CLIENT_SECRET`: Your Google Cloud OAuth Client Secret.
    -   `GMAIL_REFRESH_TOKEN`: The refresh token you generated.
    -   `NOTION_API_KEY`: Your Notion internal integration token.
    -   `NOTION_DATABASE_ID`: Your Notion database ID.
    -   `NOTION_WORKFLOW_DATABASE_ID`: Your Notion database ID for workflow tracking.
    -   `GEMINI_API_KEY`: Your Google Gemini API key.
    -   `LOG_LEVEL`: (Optional) The logging level for the application (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Defaults to `WARNING`.

The `process-bills.yml` workflow is configured to run daily every 6 hours UTC (`0 */6 * * *`) and can also be triggered manually via `workflow_dispatch`.

## License

This project is licensed under the MIT License.
