# Notion Bill Tracker

Automates bill tracking by extracting transaction info from Gmail and writing it to a Notion database. Uses DSPy with multi-provider LLM fallback for structured extraction.

## Public notion demo
[Bill tracker](https://www.notion.so/public-27f55a34994980c086e6fe771fecea91?source=copy_link) — personal bill tracking & workflow run history.

## Features

- **Gmail Integration**: Fetches unread emails based on `query` and `sender_filter` in `config/gmail_config.yaml`. `sender_filter` supports partial, case-insensitive matching (e.g., `"Chase"` matches `"JPMorgan Chase"`).
- **Double-Counting Prevention**: `exclude_merchants` skips specific merchants (e.g., `"CITI AUTOPAY"` appearing in Chase emails is ignored since Citi sends its own bill separately).
- **Multi-Provider LLM Fallback**: DSPy-powered extraction tries DeepSeek → Gemini → MiniMax in order. Each provider gets independent retries (exponential backoff); failure cascades to the next. Set at least one of `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` / `MINIMAX_API_KEY`.
- **Structured Extraction**: Pydantic model + DSPy Signature extracts:
  - `merchant` — merchant name
  - `amount` — transaction amount
  - `bill_category` — category (`餐饮`, `娱乐/购物`, `水电网费`, `房租`, `车租和保险`, `其他`)
  - `date` — transaction date (`YYYY-MM-DD`)
  - `expense_type` — `支出` (expense) or `收入` (income); defaults to `支出` when uncertain
- **Dynamic Bill Category Mapping**: `config/bill_categories.yaml` maps merchant keywords to categories (e.g., `"PROG GARDEN ST"` → `"车租和保险"`), injected into the DSPy prompt at extraction time.
- **Notion Database Management**: Writes extracted bills to a Notion database with properties: `支出项目`, `支出金额`, `支出类别`, `支出 vs. 收入`, `覆写日期`.
- **Workflow Tracking**: Each run logs status, commit ID, workflow URL, and trigger actor to a separate Notion database.
- **Configurable Logging**: Sensitive data (email subject/body, extracted bill details) is logged at `DEBUG` level only. Aggregate stats (total, processed, skipped) are at `INFO`. Defaults to `WARNING` — no transaction data exposed in public logs. Controlled via `LOG_LEVEL` env var.

## Output example
### Bill view
![alt text](demo/image.png)
![alt text](demo/image-1.png)
### Workflow view
![alt text](demo/image-2.png)
![alt text](demo/image-3.png)
![alt text](demo/image-4.png)

## Project Structure

```
notion-bills-tracker/
├── .github/
│   └── workflows/
│       ├── process-bills.yml    # Scheduled + manual trigger
│       └── get_secret.yaml      # Debug: verify secrets injection
├── config/
│   ├── bill_categories.yaml     # Merchant → category mapping
│   ├── gmail_config.yaml        # Gmail query, sender_filter, exclude_merchants
│   └── notion_config.yaml       # Notion database IDs
├── src/
│   ├── __init__.py
│   ├── main.py                  # Main pipeline
│   ├── gmail_client.py          # Gmail API wrapper
│   ├── bill_processor.py        # DSPy + multi-provider extraction
│   ├── notion_client.py         # Notion API wrapper
│   └── logger_utils.py          # Structured logging
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/TIMHX/notion-bills-tracker.git
cd notion-bills-tracker
```

### 2. Set up Python Environment with uv

```bash
uv venv
source .venv/bin/activate
uv sync
```

### 3. Configuration Files

#### `config/gmail_config.yaml`
```yaml
query: "is:unread label:账单 -in:inbox"
sender_filter: ["Chase", "citi"]
# Skip specific merchants to prevent double counting.
# Example: CITI AUTOPAY appears in both Chase and Citi bills —
# excluding it here means only the Citi-originated bill is recorded.
exclude_merchants: ["CITI AUTOPAY"]
```

#### `config/bill_categories.yaml`
Merchant keyword → category mapping, injected into the DSPy prompt:
```yaml
PROG GARDEN ST: 车租和保险
TOYOTA: 车租和保险
PUBLIC SERVICE: 水电网费
OPTIMUM: 水电网费
EVERYDAY: 餐饮
PPK CAFÉ: 餐饮
CITI AUTOPAY: 娱乐/购物
COSTCO: 娱乐/购物
```

### 4. Google Cloud & Gmail API Setup

1.  Create a project in [Google Cloud Console](https://console.cloud.google.com/) and enable the **Gmail API**.
2.  Configure the OAuth consent screen (External) with these scopes:
    - `https://www.googleapis.com/auth/gmail.readonly`
    - `https://www.googleapis.com/auth/gmail.modify`
3.  Create an OAuth client ID (Web application) with redirect URI `https://developers.google.com/oauthplayground`. Note the **Client ID** and **Client Secret**.
4.  Go to the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) → gear icon → check "Use your own OAuth credentials" and enter your Client ID/Secret. Paste the scopes, authorize, and exchange for a **Refresh Token**.

### 5. LLM API Keys (at least one required)

| Provider | Get Key From | Env Variable |
|---|---|---|
| DeepSeek (fast, cheap) | [platform.deepseek.com](https://platform.deepseek.com/) | `DEEPSEEK_API_KEY` |
| Gemini (reliable, free tier) | [Google AI Studio](https://aistudio.google.com/app/apikey) | `GEMINI_API_KEY` |
| MiniMax (fallback) | [minimaxi.com](https://www.minimaxi.com/) | `MINIMAX_API_KEY` |

### 6. Notion Integration

1.  Create an integration at [Notion Integrations](https://www.notion.so/my-integrations) → copy the **Internal Integration Token**.
2.  Create a bill database with these properties (case-sensitive Chinese names):

    | Property Name | Type |
    |---|---|
    | `支出项目` | Title |
    | `支出金额` | Number |
    | `支出类别` | Select (options: 餐饮, 娱乐/购物, 水电网费, 房租, 车租和保险, 其他) |
    | `支出 vs. 收入` | Select (options: 支出, 收入) |
    | `覆写日期` | Date |

3.  Create a separate workflow tracking database (any schema — the code matches by property name).
4.  Share both databases with your integration.
5.  Copy each Database ID from the URL (the segment after `https://www.notion.so/` and before `?v=`).

### 7. Environment Variables

Create a `.env` for local development:

```env
# Gmail OAuth (required)
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token

# Notion (required)
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_bill_database_id
NOTION_WORKFLOW_DATABASE_ID=your_workflow_database_id

# LLM (at least one)
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=AIza...
MINIMAX_API_KEY=eyJ...

# Optional
LOG_LEVEL=WARNING  # WARNING | INFO | DEBUG (DEBUG prints full email body — debug only)
```

## Running Locally

```bash
python src/main.py
```

Uses the refresh token to authenticate with Gmail — no browser interaction needed after setup.

## GitHub Actions Setup

1.  Repository → Settings → Secrets and variables → Actions → add these secrets:

    | Secret | Description |
    |---|---|
    | `GMAIL_CLIENT_ID` | Google OAuth Client ID |
    | `GMAIL_CLIENT_SECRET` | Google OAuth Client Secret |
    | `GMAIL_REFRESH_TOKEN` | Gmail refresh token |
    | `NOTION_API_KEY` | Notion integration token |
    | `NOTION_DATABASE_ID` | Bill database ID |
    | `NOTION_WORKFLOW_DATABASE_ID` | Workflow tracking database ID |
    | `DEEPSEEK_API_KEY` | DeepSeek API key |
    | `GEMINI_API_KEY` | Gemini API key |
    | `MINIMAX_API_KEY` | MiniMax API key |
    | `LOG_LEVEL` | (Optional) Defaults to `WARNING`. Set to `DEBUG` for troubleshooting only |

2.  The workflow runs automatically **every 12 hours** and can be triggered manually via `workflow_dispatch` in the Actions tab.

3.  `get_secret.yaml`: a debug workflow to verify secrets are correctly injected. Only triggerable by repo collaborators (workflow_dispatch on public repos is not visible to non-collaborators).

## License

MIT License.
