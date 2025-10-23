# Notion Bill Tracker Constitution

## Core Principles

### I. Automation-First
The primary goal is to automate the entire bill-tracking workflow, from email fetching to Notion entry. Manual intervention should be minimized.

### II. AI-Powered Data Extraction
Leverage advanced AI models (like Google Gemini) via structured frameworks (`dspy`) for reliable and accurate information extraction. Fragile, monolithic prompts are to be avoided in favor of modular and optimizable AI pipelines.

### III. Structured & Modular Code
The codebase must be modular, with clear separation of concerns (e.g., `gmail_client`, `gemini_processor`, `notion_client`). Data interchange must use well-defined schemas, such as Pydantic models.

### IV. Configuration over Hardcoding
Critical parameters, including API keys, database IDs, and business logic mappings (like bill categories), must be externalized into configuration files (`.env`, `config/bill_categories.yaml`) and not hardcoded.

### V. Observability
The system must provide clear visibility into its operational health. This includes structured, configurable logging and a dedicated workflow for tracking the status of automated runs in Notion.

## Technology Stack

### Core Technologies
- **Language:** Python >=3.13
- **Dependency Management:** `uv`
- **Core APIs:** Google Gmail API, Google Gemini API, Notion API
- **AI Framework:** `dspy-ai` for structured AI development
- **Configuration:** `python-dotenv` for secrets, `PyYAML` for data mappings.
- **Dependencies**: All dependencies must be explicitly listed in `pyproject.toml`.

## Development Workflow

### Environment & Secrets
- All development must be conducted within a `uv` virtual environment to ensure dependency isolation.
- Credentials and sensitive information must be managed using environment variables and never be committed to version control. A `.gitignore` entry for `.env` files is mandatory.

### Automation
- The primary execution environment is GitHub Actions. The workflow is defined in `.github/workflows/process-bills.yml` and should be maintained for scheduled and manual runs.

## Governance

### Compliance and Evolution
- All code contributions must adhere to the principles and standards outlined in this constitution.
- Changes to the core data schema or fundamental architecture require an update to this constitution and relevant documentation.

**Version**: 1.0.0 | **Ratified**: 2025-10-23 | **Last Amended**: N/A
