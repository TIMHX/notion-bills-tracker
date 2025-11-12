import os
from datetime import datetime
import yaml  # Import the yaml library
from gmail_client import GmailClient
from gemini_processor import GeminiProcessor
from notion_client import NotionClient
from dotenv import load_dotenv
from logger_utils import setup_logger


def main():
    load_dotenv()
    log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
    logger = setup_logger(__name__, log_level_str)

    # Load gmail config
    with open("config/gmail_config.yaml", "r") as f:
        gmail_config = yaml.safe_load(f)

    sender_filter = gmail_config.get("sender_filter", [])

    gmail_client = GmailClient(log_level_str=log_level_str)
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    notion_api_key = os.environ.get("NOTION_API_KEY")
    notion_database_id = os.environ.get("NOTION_DATABASE_ID")
    notion_workflow_database_id = os.environ.get("NOTION_WORKFLOW_DATABASE_ID")

    if not all(
        [
            gemini_api_key,
            notion_api_key,
            notion_database_id,
            notion_workflow_database_id,
        ]
    ):
        logger.error(
            "One or more environment variables (GEMINI_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID, NOTION_WORKFLOW_DATABASE_ID) are not set."
        )
        # Exit or raise an exception as appropriate for your application
        # For now, we'll set workflow_status to Failure and log it.
        workflow_status = "Failed"
        workflow_notes = "Missing environment variables."
        # We can't proceed without these, so we'll return here.
        return

    gemini_processor = GeminiProcessor(gemini_api_key, log_level_str=log_level_str)
    notion_client = NotionClient(
        notion_api_key,
        notion_database_id,
        notion_workflow_database_id,
        log_level_str=log_level_str,
    )

    workflow_name = "Process Bills Workflow"
    workflow_status = "Success"
    workflow_notes = "Successfully processed all bills."

    # Get GitHub Actions environment variables
    github_repository = os.getenv("GITHUB_REPOSITORY")
    github_run_id = os.getenv("GITHUB_RUN_ID")
    github_sha = os.getenv("GITHUB_SHA")
    github_actor = os.getenv("GITHUB_ACTOR")

    workflow_url = (
        f"https://github.com/{github_repository}/actions/runs/{github_run_id}"
        if github_repository and github_run_id
        else None
    )

    try:
        unread_emails = gmail_client.get_unread_emails(sender_filter=sender_filter)
        logger.info(f"Found {len(unread_emails)} unread emails.")

        for email in unread_emails:
            bill_info = gemini_processor.extract_bill_info(
                email_body=email["body"], email_subject=email["subject"]
            )
            if bill_info:
                logger.info(f"Extracted bill: {bill_info}")
                notion_client.add_bill_to_notion(bill_info)
                gmail_client.mark_email_as_read(email["id"])
                logger.info(f"Processed email {email['id']} and added bill to Notion.")
            else:
                logger.info(f"No bill information found in email {email['id']}.")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        workflow_status = "Failed"
        workflow_notes = f"Workflow failed with error: {e}"
    finally:
        notion_client.log_workflow_run(
            workflow_name=workflow_name,
            status=workflow_status,
            commit_id=github_sha,
            workflow_url=workflow_url,
            repository=github_repository,
            date=datetime.now().isoformat(),
            notes=workflow_notes,
            triggered_by=github_actor,
        )
        logger.info(f"Workflow run logged to Notion with status: {workflow_status}")


if __name__ == "__main__":
    main()
