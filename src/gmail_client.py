import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    def __init__(self):
        self.service = self._authenticate_gmail()

    def _authenticate_gmail(self):
        creds = Credentials(
            None,  # access_token is not needed for initial refresh
            refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN"),
            client_id=os.environ.get("GMAIL_CLIENT_ID"),
            client_secret=os.environ.get("GMAIL_CLIENT_SECRET"),
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return build("gmail", "v1", credentials=creds)

    def get_unread_emails(self, sender_filter=None):
        query = "is:unread label:大通银行明细"
        if sender_filter:
            query += f" from:{sender_filter}"
        results = self.service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        unread_emails_data = []
        for message in messages:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message["id"], format="full")
                .execute()
            )
            payload = msg["payload"]
            headers = payload["headers"]
            subject = next(
                (header["value"] for header in headers if header["name"] == "Subject"),
                "No Subject",
            )
            sender = next(
                (header["value"] for header in headers if header["name"] == "From"),
                "Unknown Sender",
            )

            # Extract body (handling multipart messages)
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = self._decode_email_body(part["body"]["data"])
                        break
            else:
                body = self._decode_email_body(payload["body"]["data"])

            unread_emails_data.append(
                {
                    "id": message["id"],
                    "subject": subject,
                    "sender": sender,
                    "body": body,
                }
            )
        return unread_emails_data

    def mark_email_as_read(self, message_id):
        self.service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    def _decode_email_body(self, data):
        import base64

        return base64.urlsafe_b64decode(data).decode("utf-8")


if __name__ == "__main__":
    # Example usage (replace with your credentials.json path)
    # Ensure you have a credentials.json file from Google Cloud Platform
    # and enable the Gmail API.
    # You'll also need to run this script once locally to authenticate
    # and generate the token.pickle file.
    gmail_client = GmailClient()
    unread_emails = gmail_client.get_unread_emails()
    for email in unread_emails:
        print(f"Subject: {email['subject']}, Sender: {email['sender']}")
        print(f"Body: {email['body'][:200]}...")  # Print first 200 chars of body
        gmail_client.mark_email_as_read(email["id"])
        break
    pass
