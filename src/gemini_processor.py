import dspy
import json
import os
from dotenv import load_dotenv
from logger_utils import setup_logger
from pydantic import BaseModel, Field
from typing import Optional
import yaml  # Added for YAML parsing


# Define a Pydantic model for structured bill information.
class BillInfo(BaseModel):
    """A structured representation of bill information."""

    merchant: Optional[str] = Field(
        default=None, description="The merchant's name (e.g., 'BARCLAY VILLAGE')."
    )
    amount: Optional[float] = Field(
        default=None, description="The bill amount as a numeric value."
    )
    bill_category: Optional[str] = Field(
        default=None,
        description="The bill_category, select within the following: ('餐饮', '娱乐/购物', '水电网费', '房租', '车租和保险', '其他').",
    )
    date: Optional[str] = Field(
        default=None, description="The date of the transaction in 'YYYY-MM-DD' format."
    )


# Define the signature for bill information extraction using the Pydantic model.
class BillInfoSignature(dspy.Signature):
    """
    Defines the input and output fields for the AI model, creating a structured
    and enforceable schema. This programmatic approach to prompting is a core
    benefit of DSPy, replacing manually crafted and brittle prompt strings.
    """

    email_subject: str = dspy.InputField(desc="The subject of an email.")
    email_body: str = dspy.InputField(desc="The body of an email.")
    bill_info: BillInfo = dspy.OutputField(
        desc="Structured bill information based on the Pydantic model."
    )


# Define the DSPy module for bill extraction using ChainOfThought.
class BillExtractor(dspy.Module):
    """
    A DSPy Module encapsulates the prompting strategy. It defines how different
    components (like signatures and optimizers) are composed to solve a task.
    This modularity makes the AI pipeline easier to manage, test, and optimize.
    """

    def __init__(self, bill_category_mapping: dict):
        super().__init__()
        # Dynamically create the BillInfoSignature with the mapping in the description
        mapping_str = "\n".join(
            [
                f"- If merchant contains '{k}', category is '{v}'"
                for k, v in bill_category_mapping.items()
            ]
        )
        updated_bill_category_desc = (
            "The bill_category, select within the following: ('餐饮', '娱乐/购物', '水电网费', '房租', '车租和保险', '其他'). "
            "Consider the following rules for categorization:\n"
            f"{mapping_str}"
        )

        class DynamicBillInfoSignature(dspy.Signature):
            email_subject: str = dspy.InputField(desc="The subject of an email.")
            email_body: str = dspy.InputField(desc="The body of an email.")
            bill_info: BillInfo = dspy.OutputField(
                desc="Structured bill information based on the Pydantic model.",
                json_schema_extra={
                    "properties": {
                        "bill_category": {"description": updated_bill_category_desc}
                    }
                },
            )

        # ChainOfThought is a DSPy component that explicitly asks the language model
        # to "think step-by-step" before providing the final answer. This improves
        # reasoning and leads to more accurate and reliable structured data extraction.
        self.extractor = dspy.ChainOfThought(DynamicBillInfoSignature)

    def forward(self, email_subject, email_body):
        # The forward method defines the execution logic of the module.
        prediction = self.extractor(email_subject=email_subject, email_body=email_body)
        return prediction


class GeminiProcessor:
    def __init__(self, api_key, log_level_str: str = "WARNING"):
        self.logger = setup_logger(__name__, log_level_str)
        self.bill_category_mapping = self._load_bill_category_mapping()
        try:
            # Configure DSPy with the Gemini model and JSON adapter for Pydantic.
            gemini_lm = dspy.LM(
                "gemini/gemini-2.5-flash", api_key=api_key, max_tokens=2048
            )
            dspy.configure(lm=gemini_lm, adapter=dspy.ChatAdapter())
            self.bill_extractor = BillExtractor(self.bill_category_mapping)
            self.logger.info("DSPy configured successfully with Gemini model.")
        except Exception as e:
            self.logger.error(f"Failed to configure DSPy with Gemini: {e}")
            raise

    def _load_bill_category_mapping(
        self, config_path: str = "config/bill_categories.yaml"
    ):
        """Loads the bill category mapping from a YAML file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                mapping = yaml.safe_load(f)
            self.logger.info(
                f"Successfully loaded bill category mapping from {config_path}"
            )
            return mapping
        except FileNotFoundError:
            self.logger.error(f"Bill category mapping file not found at {config_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML file {config_path}: {e}")
            return {}

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
