import google.generativeai as genai
import json
import os
from dotenv import load_dotenv


class GeminiProcessor:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def extract_bill_info(self, email_body, email_subject=""):
        prompt = f"""
        Analyze the following email body, specifically looking for Chase bill information.
        Look for details like:
        - amount (numeric value)
        - merchant (e.g., "BARCLAY VILLAGE", "10162 CAVA LAWRENCEV")
        - account_type (determine if it's "支票账户" for checking account or "信用卡" for credit card based on keywords like "account ending in" for checking or "transaction with" for credit card)
        - date (e.g. transform "Sep 3, 2025 at 6:19 PM ET" into "2025-09-03")

        If you find the information, return it as a JSON object.
        If you don't find sufficient information, return an empty JSON object.

        Email Body:
        ---
        {email_body}
        ---

        JSON Output:
        """
        try:
            print(f"Sending the following prompt to Gemini:\n{prompt}")
            response = self.model.generate_content(prompt)
            json_output = response.text.strip()
            # Remove markdown code block if present
            if json_output.startswith("```json") and json_output.endswith("```"):
                json_output = json_output[7:-3].strip()
            try:
                bill_info = json.loads(json_output)
            except json.JSONDecodeError:
                print(f"Gemini returned non-JSON response: {json_output}")
                return {}

            if "amount" in bill_info and isinstance(bill_info["amount"], str):
                try:
                    # Remove currency symbols and commas, then convert to float
                    amount_str = bill_info["amount"].replace("$", "").replace(",", "")
                    bill_info["amount"] = float(amount_str)
                except (ValueError, TypeError):
                    print(f"Could not convert amount to float: {bill_info['amount']}")

            return bill_info
        except Exception as e:
            print(f"Error extracting bill info with Gemini: {e}")
            return {}


if __name__ == "__main__":
    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")

    gemini_processor = GeminiProcessor(gemini_api_key)
    # Updated sample email body to include keywords for account type detection
    sample_email_body = """
    You sent $1,635.00 to Testing VILLAGE from account ending in (...3925)

    Account ending in (...3925)
    Sent on 	Sep 4, 2025 at 4:29 PM ET
    Recipient 	Testing VILLAGE
    Amount 	$1,635.00
    """
    bill_details = gemini_processor.extract_bill_info(sample_email_body)
    # Ensure proper display of Chinese characters
    print(json.dumps(bill_details, ensure_ascii=False, indent=2))
    pass
