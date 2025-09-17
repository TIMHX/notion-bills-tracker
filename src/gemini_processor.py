import dspy
import json
import os
from dotenv import load_dotenv
from logger_utils import setup_logger
from pydantic import BaseModel, Field
from typing import Optional


# Define a Pydantic model for structured bill information.
class BillInfo(BaseModel):
    """A structured representation of bill information."""

    merchant: Optional[str] = Field(
        default=None, description="The merchant's name (e.g., 'BARCLAY VILLAGE')."
    )
    amount: Optional[float] = Field(
        default=None, description="The bill amount as a numeric value."
    )
    account_type: Optional[str] = Field(
        default=None, description="The account type ('支票账户', '信用卡', '餐饮')."
    )
    date: Optional[str] = Field(
        default=None, description="The date of the transaction in 'YYYY-MM-DD' format."
    )


# Define the signature for bill information extraction using the Pydantic model.
class BillInfoSignature(dspy.Signature):
    """Analyze the email body to extract bill information and return a structured object."""

    email_subject: str = dspy.InputField(desc="The subject of an email.")
    email_body: str = dspy.InputField(desc="The body of an email.")
    bill_info: BillInfo = dspy.OutputField(desc="Structured bill information.")


# Define the DSPy module for bill extraction using ChainOfThought.
class BillExtractor(dspy.Module):
    def __init__(self):
        super().__init__()
        # Use ChainOfThought to encourage reasoning before producing the final structured output.
        self.extractor = dspy.ChainOfThought(BillInfoSignature)

    def forward(self, email_subject, email_body):
        prediction = self.extractor(email_subject=email_subject, email_body=email_body)
        return prediction


class GeminiProcessor:
    def __init__(self, api_key, log_level_str: str = "WARNING"):
        self.logger = setup_logger(__name__, log_level_str)
        try:
            # Configure DSPy with the Gemini model and JSON adapter for Pydantic.
            gemini_lm = dspy.LM(
                "gemini/gemini-1.5-flash", api_key=api_key, max_tokens=2048
            )
            dspy.configure(lm=gemini_lm, adapter=dspy.ChatAdapter())
            self.bill_extractor = BillExtractor()
            self.logger.info("DSPy configured successfully with Gemini model.")
        except Exception as e:
            self.logger.error(f"Failed to configure DSPy with Gemini: {e}")
            raise

    def extract_bill_info(
        self, email_body: str, email_subject: str = ""
    ) -> Optional[BillInfo]:
        """
        Extracts bill information from an email body using a DSPy module.

        Args:
            email_body: The text content of the email.
            email_subject: The subject of the email.

        Returns:
            A Pydantic BillInfo object or None if extraction fails.
        """
        try:
            self.logger.debug(
                f"Extracting bill info from email subject: '{email_subject}' and body:\n{email_body}"
            )
            prediction = self.bill_extractor(
                email_subject=email_subject, email_body=email_body
            )

            # The output is now a Pydantic object, so we can access its fields directly.
            bill_info = prediction.bill_info
            self.logger.info(f"Successfully extracted bill info: {bill_info}")
            return bill_info
        except Exception as e:
            self.logger.error(f"Error extracting bill info with DSPy: {e}")
            # Log the full traceback for debugging
            self.logger.debug(e, exc_info=True)
            return None


if __name__ == "__main__":
    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")

    gemini_processor = GeminiProcessor(gemini_api_key, log_level_str=log_level_str)

    sample_email_subject = "You sent a payment to Testing VILLAGE"
    sample_email_body = """
    You sent $1,635.00 to Testing VILLAGE from account ending in (...3925)

    Account ending in (...3925)
    Sent on 	Sep 4, 2025 at 4:29 PM ET
    Recipient 	Testing VILLAGE
    Amount 	$1,635.00
    """
    bill_details = gemini_processor.extract_bill_info(
        sample_email_body, sample_email_subject
    )

    if bill_details:
        # Convert Pydantic model to a dictionary for JSON serialization
        bill_details_dict = bill_details.model_dump()
        gemini_processor.logger.info(
            "Extracted bill details: %s",
            json.dumps(bill_details_dict, ensure_ascii=False, indent=2),
        )
    else:
        gemini_processor.logger.warning("Could not extract bill details.")
