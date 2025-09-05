import os
import pickle
import re
from bs4 import BeautifulSoup
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
                    if part["mimeType"] == "text/html":
                        body = self._decode_email_body(part["body"]["data"])
                        break
                    if part["mimeType"] == "text/plain":
                        body = self._decode_email_body(part["body"]["data"])
                        break
            else:
                body = self._decode_email_body(payload["body"]["data"])

            body = self._clean_email_body(body)

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

    def _clean_email_body(self, body: str) -> str:
        """Cleans the email body by removing signatures, quoted text, and excessive whitespace."""
        soup = BeautifulSoup(body, "lxml")
        # Get text from the body
        text = soup.get_text()
        # Remove forwarded message headers
        text = re.sub(r"---------- Forwarded message ---------.*", "", text, flags=re.DOTALL)
        # Remove "On <date>, <author> wrote:" lines
        text = re.sub(r"On.*wrote:", "", text, flags=re.DOTALL)
        # Remove quoted text (lines starting with '>')
        text = re.sub(r"(\n>.*)+", "", text)
        # Remove signatures (lines starting with '--')
        text = re.sub(r"\n--.*", "", text, flags=re.DOTALL)
        # Remove irrelevant alert information
        text = re.sub(
            r"You are receiving this alert because.*account\.", "", text, flags=re.DOTALL
        )
        text = re.sub(r"Review account", "", text)
        text = re.sub(r"Securely access your accounts with.*chase\.com\.", "", text)
        # Remove "About this message" section
        text = re.sub(r"About this message.*", "", text, flags=re.DOTALL)
        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


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
