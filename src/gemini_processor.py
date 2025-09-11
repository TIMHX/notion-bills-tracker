import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
from logger_utils import setup_logger  # Added import


class GeminiProcessor:
    # Modified __init__ to accept log_level_str and setup logger
    def __init__(self, api_key, log_level_str: str = "WARNING"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

        self.logger = setup_logger(__name__, log_level_str)  # Use the universal logger

    def extract_bill_info(self, email_body, email_subject=""):
        prompt = f"""
        Analyze the following email body, specifically looking for bill information.
        Look for details like:
        - amount (numeric value)
        - merchant (e.g., "BARCLAY VILLAGE", "10162 CAVA LAWRENCEV", "PPK Café")
        - account_type (determine if it's "支票账户" for checking account or "信用卡" for credit card or "餐饮" for diner based on keywords like "account ending in" for checking or "transaction with" for credit card or "Everyday app" for diner)
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
            # Replaced print with logger.debug
            self.logger.debug(f"Sending the following prompt to Gemini:\n{prompt}")
            response = self.model.generate_content(prompt)
            json_output = response.text.strip()
            # Remove markdown code block if present
            if json_output.startswith("```json") and json_output.endswith("```"):
                json_output = json_output[7:-3].strip()
            try:
                bill_info = json.loads(json_output)
            except json.JSONDecodeError:
                # Replaced print with logger.warning
                self.logger.warning(f"Gemini returned non-JSON response: {json_output}")
                return {}

            if "amount" in bill_info and isinstance(bill_info["amount"], str):
                try:
                    # Remove currency symbols and commas, then convert to float
                    amount_str = bill_info["amount"].replace("$", "").replace(",", "")
                    bill_info["amount"] = float(amount_str)
                except (ValueError, TypeError):
                    # Replaced print with logger.warning
                    self.logger.warning(
                        f"Could not convert amount to float: {bill_info['amount']}"
                    )

            return bill_info
        except Exception as e:
            # Replaced print with logger.error
            self.logger.error(f"Error extracting bill info with Gemini: {e}")
            return {}


if __name__ == "__main__":
    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    # Get LOG_LEVEL from env, default to WARNING
    log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()

    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")

    # Instantiate GeminiProcessor with the determined log level
    gemini_processor = GeminiProcessor(gemini_api_key, log_level_str=log_level_str)

    # Updated sample email body to include keywords for account type detection
    sample_email_body = """
    You sent $1,635.00 to Testing VILLAGE from account ending in (...3925)

    Account ending in (...3925)
    Sent on 	Sep 4, 2025 at 4:29 PM ET
    Recipient 	Testing VILLAGE
    Amount 	$1,635.00
    """
    bill_details = gemini_processor.extract_bill_info(sample_email_body)
    # Use logger.info for the final output, controlled by the log_level
    gemini_processor.logger.info(
        f"Extracted bill details: {json.dumps(bill_details, ensure_ascii=False, indent=2)}"
    )
