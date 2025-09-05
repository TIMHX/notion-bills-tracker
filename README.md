# Chase Bill Tracker

This project automates the process of tracking bills from your Gmail inbox and adding them to a Notion database. It uses the Google Gemini API to extract bill information from emails and the Notion API to manage your bill tracking.

## Features

- **Gmail Integration**: Fetches unread emails from your Gmail inbox.
- **Gemini AI Extraction**: Utilizes Google Gemini to intelligently extract bill details (name, due date, amount, currency, biller) from email content.
- **Notion Database Management**: Adds extracted bill information to a specified Notion database.
- **Automated Workflow**: Designed to run automatically via GitHub Actions on a schedule, or manually triggered.

## Project Structure

```
chase-bill-tracker/
├── .github/
│   └── workflows/
│       └── process-bills.yml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── gmail_client.py
│   ├── gemini_processor.py
│   └── notion_client.py
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/chase-bill-tracker.git
cd chase-bill-tracker
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

### 3. Google Cloud Project & Gmail API Credentials

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project or select an existing one.
3.  Enable the **Gmail API**.
4.  Go to "APIs & Services" > "Credentials".
5.  Click "Create Credentials" > "OAuth client ID".
6.  Choose "Desktop app" as the application type and create it.
7.  Download the `credentials.json` file.
8.  Place this file in the root of your `chase-bill-tracker` directory. **Do NOT commit this file to Git.**

### 4. Google Gemini API Key

1.  Go to the [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Create an API key.
3.  **Do NOT commit this key to Git.**

### 5. Notion Integration Token & Database ID

1.  Go to your [Notion Integrations page](https://www.notion.so/my-integrations).
2.  Click "New integration".
3.  Give it a name (e.g., "Bill Tracker Integration") and associate it with your workspace.
4.  Copy the "Internal Integration Token".
5.  Create a new Notion database for your bills. It should have the following properties (case-sensitive):
    -   `Bill Name` (Title)
    -   `Due Date` (Date)
    -   `Amount Due` (Number)
    -   `Currency` (Rich Text)
    -   `Biller` (Rich Text)
6.  Share your Notion database with the integration you just created.
7.  Copy the Database ID from the URL of your Notion database. It's the part after `https://www.notion.so/` and before `?v=...`.

### 6. Environment Variables

Create a `.env` file in the root of your project with the following variables:

```
GMAIL_CREDENTIALS_PATH=./credentials.json
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
NOTION_API_KEY=YOUR_NOTION_API_KEY
NOTION_DATABASE_ID=YOUR_NOTION_DATABASE_ID
```

Replace `YOUR_GEMINI_API_KEY`, `YOUR_NOTION_API_KEY`, and `YOUR_NOTION_DATABASE_ID` with your actual keys and IDs.

## Running Locally

```bash
python src/main.py
```

The first time you run `src/main.py`, a browser window will open for you to authenticate with your Google account for Gmail access. After successful authentication, a `token.pickle` file will be created to store your credentials for future runs.

## GitHub Actions Setup

To run this project automatically on GitHub Actions, you need to set up repository secrets:

1.  Go to your GitHub repository settings.
2.  Navigate to "Secrets and variables" > "Actions".
3.  Add the following repository secrets:
    -   `GMAIL_CREDENTIALS_PATH`: The content of your `credentials.json` file. **Copy the entire JSON content directly into the secret value.**
    -   `NOTION_API_KEY`: Your Notion internal integration token.
    -   `NOTION_DATABASE_ID`: Your Notion database ID.
    -   `GEMINI_API_KEY`: Your Google Gemini API key.

The `process-bills.yml` workflow is configured to run daily at midnight UTC and can also be triggered manually.

## License

This project is licensed under the MIT License.
