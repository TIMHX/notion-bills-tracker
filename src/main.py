import os
from gmail_client import GmailClient
from gemini_processor import GeminiProcessor
from notion_client import NotionClient
from dotenv import load_dotenv


def main():
    load_dotenv()
    # Initialize clients
    gmail_client = GmailClient(os.environ.get("GMAIL_CREDENTIALS_PATH"))
    gemini_processor = GeminiProcessor(os.environ.get("GEMINI_API_KEY"))
    notion_client = NotionClient(
        os.environ.get("NOTION_API_KEY"), os.environ.get("NOTION_DATABASE_ID")
    )

    # 1. Fetch unread emails from Chase
    unread_emails = gmail_client.get_unread_emails(sender_filter="Chase")
    print(f"Found {len(unread_emails)} unread emails.")

    for email in unread_emails:
        # 2. Extract bill information using Gemini
        bill_info = gemini_processor.extract_bill_info(email["body"])
        if bill_info:
            print(f"Extracted bill: {bill_info}")
            # 3. Add to Notion
            notion_client.add_bill_to_notion(bill_info)
            # 4. Mark email as read
            gmail_client.mark_email_as_read(email["id"])
            print(f"Processed email {email['id']} and added bill to Notion.")
        else:
            print(f"No bill information found in email {email['id']}.")


if __name__ == "__main__":
    main()
