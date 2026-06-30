import os
from datetime import datetime
import yaml
from gmail_client import GmailClient
from bill_processor import BillProcessor
from notion_client import NotionClient
from dotenv import load_dotenv
from logger_utils import setup_logger


def main():
    load_dotenv()
    log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
    logger = setup_logger(__name__, log_level_str)

    # Load gmail config
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "gmail_config.yaml"
    )
    with open(config_path, "r") as f:
        gmail_config = yaml.safe_load(f)

    sender_filter = gmail_config.get("sender_filter", [])
    exclude_merchants = gmail_config.get("exclude_merchants", [])

    gmail_client = GmailClient(log_level_str=log_level_str)
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
    minimax_api_key = os.environ.get("MINIMAX_API_KEY")
    notion_api_key = os.environ.get("NOTION_API_KEY")
    notion_database_id = os.environ.get("NOTION_DATABASE_ID")
    notion_workflow_database_id = os.environ.get("NOTION_WORKFLOW_DATABASE_ID")

    # Notion keys are mandatory; at least one LLM provider key is required
    if not all([notion_api_key, notion_database_id, notion_workflow_database_id]):
        logger.error(
            "Missing Notion env vars (NOTION_API_KEY, NOTION_DATABASE_ID, "
            "NOTION_WORKFLOW_DATABASE_ID)."
        )
        workflow_status = "Failed"
        workflow_notes = "Missing Notion environment variables."
        return

    if not any([deepseek_api_key, gemini_api_key, minimax_api_key]):
        logger.error(
            "No LLM API key configured. Set at least one of: "
            "DEEPSEEK_API_KEY, GEMINI_API_KEY, MINIMAX_API_KEY."
        )
        workflow_status = "Failed"
        workflow_notes = "Missing LLM API key."
        return

    bill_processor = BillProcessor(gemini_api_key, log_level_str=log_level_str)
    notion_client = NotionClient(
        notion_api_key,
        notion_database_id,
        notion_workflow_database_id,
        log_level_str=log_level_str,
    )

    workflow_name = "Process Bills Workflow"
    workflow_status = "Skipped"  # default; updated below
    workflow_notes = ""

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
        logger.info(f"sender_filter: {sender_filter}")
        logger.info(f"Found {len(unread_emails)} unread emails.")

        # Track per-email outcomes for accurate status reporting
        count_processed = 0
        count_skipped = 0
        count_empty = 0
        count_errors = 0
        failed_ids = []

        for email in unread_emails:
            try:
                logger.debug(f"Processing email {email['id']}: {email['subject']}")
                logger.debug(f"Sender: {email['sender']}")
                logger.debug(f"Body: {email['body']}")
                bill_info = bill_processor.extract_bill_info(
                    email_body=email["body"], email_subject=email["subject"]
                )
                if bill_info.merchant:
                    # 检查是否应该排除该 merchant（避免 double counting）
                    merchant_lower = (bill_info.merchant or "").lower()
                    excluded = any(
                        ex.lower() in merchant_lower for ex in exclude_merchants
                    )
                    if excluded:
                        logger.info(
                            f"Skipping excluded merchant '{bill_info.merchant}' "
                            f"in email {email['id']}. Marking as read anyway."
                        )
                        gmail_client.mark_email_as_read(email["id"])
                        count_skipped += 1
                        continue

                    logger.debug(f"Extracted bill: {bill_info}")
                    result = notion_client.add_bill_to_notion(bill_info)
                    if result is None:
                        logger.error(
                            f"Failed to add bill to Notion for email {email['id']}. "
                            "Email will NOT be marked as read so it can be retried."
                        )
                        count_errors += 1
                        failed_ids.append(email["id"])
                        continue
                    gmail_client.mark_email_as_read(email["id"])
                    count_processed += 1
                    logger.debug(f"Processed email {email['id']} and added bill to Notion.")
                else:
                    # No bill info extracted — mark as read to avoid reprocessing
                    logger.info(
                        f"No bill information found in email {email['id']}. "
                        "Marking as read."
                    )
                    gmail_client.mark_email_as_read(email["id"])
                    count_empty += 1
            except Exception as e:
                logger.error(
                    f"Failed to process email {email['id']}: {e}. "
                    "Keeping unread for retry."
                )
                count_errors += 1
                failed_ids.append(email["id"])
                continue

        # Determine final status and build notes
        total = len(unread_emails)
        parts = [f"Total: {total}", f"Processed: {count_processed}"]
        if count_skipped:
            parts.append(f"Skipped: {count_skipped}")
        if count_empty:
            parts.append(f"Empty: {count_empty}")
        if count_errors:
            parts.append(f"Errors: {count_errors}")
            if failed_ids:
                ids_str = ", ".join(failed_ids[:5])
                if len(failed_ids) > 5:
                    ids_str += f" (+{len(failed_ids) - 5} more)"
                parts.append(f"Failed IDs: {ids_str}")

        workflow_notes = "; ".join(parts)

        if total == 0:
            workflow_status = "Skipped"
            workflow_notes = "No unread emails found."
        elif count_errors > 0:
            workflow_status = "Failed"
        else:
            workflow_status = "Success"

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
