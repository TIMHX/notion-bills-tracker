import os
from gmail_client import GmailClient
from gemini_processor import GeminiProcessor
from notion_client import NotionClient
from dotenv import load_dotenv
from logger_utils import setup_logger  # Added import


def main():
    load_dotenv()
    # Get LOG_LEVEL from env, default to WARNING
    log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
    logger = setup_logger(__name__, log_level_str)  # Setup main logger

    # Initialize clients, passing the log_level_str
    gmail_client = GmailClient(log_level_str=log_level_str)
    gemini_processor = GeminiProcessor(
        os.environ.get("GEMINI_API_KEY"), log_level_str=log_level_str
    )
    notion_client = NotionClient(
        os.environ.get("NOTION_API_KEY"),
        os.environ.get("NOTION_DATABASE_ID"),
        log_level_str=log_level_str,
    )

    # 1. Fetch unread emails from Chase
    unread_emails = gmail_client.get_unread_emails(sender_filter="Chase")
    logger.info(f"Found {len(unread_emails)} unread emails.")

    for email in unread_emails:
        # 2. Extract bill information using Gemini
        bill_info = gemini_processor.extract_bill_info(email["body"])
        if bill_info:
            logger.info(f"Extracted bill: {bill_info}")
            # 3. Add to Notion
            notion_client.add_bill_to_notion(bill_info)
            # 4. Mark email as read
            gmail_client.mark_email_as_read(email["id"])
            logger.info(f"Processed email {email['id']} and added bill to Notion.")
        else:
            logger.info(f"No bill information found in email {email['id']}.")


if __name__ == "__main__":
    main()
