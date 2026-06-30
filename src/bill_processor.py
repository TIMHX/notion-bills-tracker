import dspy
import json
import os
from dotenv import load_dotenv
from logger_utils import setup_logger
from pydantic import BaseModel, Field
from typing import Optional
import yaml
from tenacity import Retrying, stop_after_attempt, wait_exponential, retry_if_exception_type


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
        default=None,
        description="The date of the transaction in 'YYYY-MM-DD' format.",
    )
    expense_type: Optional[str] = Field(
        default=None,
        description="Whether this is an expense ('支出') or income ('收入'). "
        "支出 = money going out (bill payment, purchase, transfer sent). "
        "收入 = money coming in (salary, refund, deposit, transfer received). "
        "Default to '支出' when uncertain.",
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

    def __init__(self, bill_category_mapping: dict, lm):
        super().__init__()
        # NOTE: do NOT store `self.lm = lm` — DSPy 3.x will try to JSON-serialize
        # the module's attributes, and LM objects are not serializable.
        # The LM is stored externally by BillProcessor and passed via
        # dspy.settings.context() at call time.
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
        # LM is passed directly (not global) to avoid state pollution across instances.
        self.extractor = dspy.ChainOfThought(DynamicBillInfoSignature, lm=lm)

    def forward(self, email_subject, email_body):
        # The forward method defines the execution logic of the module.
        prediction = self.extractor(email_subject=email_subject, email_body=email_body)
        return prediction


class BillProcessor:
    """Processor that extracts bill info from emails using DSPy + LLM.

    Uses a provider fallback chain: DeepSeek → Gemini → MiniMax.
    Each provider gets its own retry (exponential backoff via tenacity).
    If one provider exhausts retries, automatically switches to the next.
    Configure by setting: DEEPSEEK_API_KEY, GEMINI_API_KEY, MINIMAX_API_KEY.
    """

    def __init__(self, gemini_key=None, log_level_str: str = "WARNING"):
        self.logger = setup_logger(__name__, log_level_str)
        self.bill_category_mapping = self._load_bill_category_mapping()
        self.extractors = self._build_extractor_chain(gemini_key)
        if not self.extractors:
            raise ValueError(
                "No LLM API keys configured. "
                "Set at least one of: DEEPSEEK_API_KEY, GEMINI_API_KEY, MINIMAX_API_KEY."
            )
        names = [name for name, _, _ in self.extractors]
        self.logger.info(f"LLM provider chain: {' → '.join(names)}")

    def _build_extractor_chain(self, gemini_key):
        """Build ordered list of (name, lm, BillExtractor) from available API keys. LM is stored alongside the extractor (not on it) to avoid DSPy 3.x serialization bug."""
        extractors = []

        # 1. DeepSeek (primary — cheapest, good quality)
        ds_key = os.getenv("DEEPSEEK_API_KEY")
        if ds_key:
            try:
                # Use litellm native deepseek provider (not openai/ fallback)
                # to avoid DSPy structured-output serialization bug
                lm = dspy.LM(
                    "deepseek/deepseek-chat",
                    api_key=ds_key,
                    max_tokens=2048,
                )
                extractors.append(
                    ("DeepSeek", lm, BillExtractor(self.bill_category_mapping, lm))
                )
            except Exception as e:
                self.logger.warning(f"Failed to init DeepSeek: {e}")

        # 2. Gemini (fallback — reliable, free tier)
        if gemini_key:
            try:
                lm = dspy.LM(
                    "gemini/gemini-2.5-flash",
                    api_key=gemini_key,
                    max_tokens=2048,
                )
                extractors.append(
                    ("Gemini", lm, BillExtractor(self.bill_category_mapping, lm))
                )
            except Exception as e:
                self.logger.warning(f"Failed to init Gemini: {e}")

        # 3. MiniMax (last resort)
        mm_key = os.getenv("MINIMAX_API_KEY")
        if mm_key:
            try:
                lm = dspy.LM(
                    "openai/MiniMax-M2.7",
                    api_key=mm_key,
                    api_base="https://api.minimaxi.com/v1",
                    max_tokens=2048,
                )
                extractors.append(
                    ("MiniMax", lm, BillExtractor(self.bill_category_mapping, lm))
                )
            except Exception as e:
                self.logger.warning(f"Failed to init MiniMax: {e}")

        return extractors

    def _load_bill_category_mapping(
        self, config_filename: str = "bill_categories.yaml"
    ):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", config_filename
        )
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
    ) -> BillInfo:
        """
        Extracts bill information from an email body using DSPy.

        Tries each provider in order (DeepSeek → Gemini → MiniMax).
        Each provider gets up to 2 retries with exponential backoff
        (tenacity). On total failure, switches to the next provider.

        Args:
            email_body: The text content of the email.
            email_subject: The subject of the email.

        Returns:
            A Pydantic BillInfo object (may have None fields if no bill data
            found in the email). Raises RuntimeError if all providers fail.
        """
        last_error = None

        for name, lm, extractor in self.extractors:
            try:
                self.logger.debug(f"Trying {name}...")
                # dspy.settings.context() sets the LM for this block only
                # — no global pollution, auto-restores on exit.
                with dspy.settings.context(lm=lm):
                    for attempt in Retrying(
                        stop=stop_after_attempt(2),
                        wait=wait_exponential(multiplier=1, min=2, max=10),
                        retry=retry_if_exception_type(Exception),
                        reraise=True,
                    ):
                        with attempt:
                            prediction = extractor(
                                email_subject=email_subject, email_body=email_body
                            )
                            bill_info = prediction.bill_info
                            self.logger.info(f"✓ {name}: {bill_info}")
                            return bill_info
            except Exception as e:
                self.logger.warning(f"✗ {name} failed: {e}")
                last_error = e
                continue

        self.logger.error(
            f"All {len(self.extractors)} providers failed. Last error: {last_error}"
        )
        raise RuntimeError(
            f"All {len(self.extractors)} providers exhausted. "
            f"Last error: {last_error}"
        )


if __name__ == "__main__":
    load_dotenv()
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

    # BillProcessor supports any of: DEEPSEEK_API_KEY, GEMINI_API_KEY, MINIMAX_API_KEY
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    minimax_api_key = os.getenv("MINIMAX_API_KEY")
    if not any([deepseek_api_key, gemini_api_key, minimax_api_key]):
        raise ValueError(
            "At least one LLM API key required. "
            "Set DEEPSEEK_API_KEY, GEMINI_API_KEY, or MINIMAX_API_KEY."
        )

    bill_processor = BillProcessor(gemini_api_key, log_level_str=log_level_str)

    sample_email_subject = "You sent a payment to Testing VILLAGE"
    sample_email_body = """
    You sent $1,635.00 to Testing VILLAGE from account ending in (...3925)

    Account ending in (...3925)
    Sent on 	Sep 4, 2025 at 4:29 PM ET
    Recipient 	Testing VILLAGE
    Amount 	$1,635.00
    """
    bill_details = bill_processor.extract_bill_info(
        sample_email_body, sample_email_subject
    )

    if bill_details:
        # Convert Pydantic model to a dictionary for JSON serialization
        bill_details_dict = bill_details.model_dump()
        bill_processor.logger.info(
            "Extracted bill details: %s",
            json.dumps(bill_details_dict, ensure_ascii=False, indent=2),
        )
    else:
        bill_processor.logger.warning("Could not extract bill details.")
