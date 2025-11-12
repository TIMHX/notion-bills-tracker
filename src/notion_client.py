import requests
import json
import os
import yaml
from dotenv import load_dotenv
from logger_utils import setup_logger  # Added import
from gemini_processor import GeminiProcessor


class NotionClient:
    # Modified __init__ to accept log_level_str and setup logger
    def __init__(
        self, api_key, database_id, workflow_database_id, log_level_str: str = "WARNING"
    ):
        self.api_key = api_key
        self.database_id = database_id
        self.workflow_database_id = workflow_database_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self.logger = setup_logger(__name__, log_level_str)  # Use the universal logger

    def add_bill_to_notion(self, bill_info):
        create_page_url = "https://api.notion.com/v1/pages"

        properties = {
            "支出项目": {
                "title": [{"text": {"content": bill_info.merchant or "Unknown"}}]
            },
            "支出金额": {"number": bill_info.amount or 0.0},
            "支出类别": {"select": {"name": bill_info.bill_category or "其他"}},
            "覆写日期": {
                "date": {"start": bill_info.date or "2024-01-01"}
            },  # Default date if not found
        }

        data = {"parent": {"database_id": self.database_id}, "properties": properties}
        # Replaced print with logger.debug
        self.logger.debug(f"Sending data to Notion: {json.dumps(data, indent=2)}")

        response = requests.post(
            create_page_url, headers=self.headers, data=json.dumps(data)
        )

        if response.status_code == 200:
            # Replaced print with logger.info
            self.logger.info("Bill added to Notion successfully!")
            return response.json()
        else:
            # Replaced print with logger.error
            self.logger.error(
                f"Error adding bill to Notion: {response.status_code} - {response.text}"
            )
            return None

    def log_workflow_run(
        self,
        workflow_name,
        status,
        commit_id=None,
        duration=None,
        workflow_url=None,
        repository=None,
        date=None,
        notes=None,
        triggered_by=None,
    ):
        create_page_url = "https://api.notion.com/v1/pages"

        properties = {
            "Workflow Run": {"title": [{"text": {"content": workflow_name}}]},
            "Status": {"status": {"name": status}},
        }

        if commit_id:
            properties["Commit ID"] = {"rich_text": [{"text": {"content": commit_id}}]}
        if duration is not None:
            properties["Duration"] = {"number": duration}
        if workflow_url:
            properties["Workflow URL"] = {"url": workflow_url}
        if repository:
            properties["Repository"] = {
                "rich_text": [{"text": {"content": repository}}]
            }
        if date:
            properties["Date"] = {"date": {"start": date}}
        if notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
        if triggered_by:
            properties["Triggered By"] = {"select": {"name": triggered_by}}

        data = {
            "parent": {"database_id": self.workflow_database_id},
            "properties": properties,
        }
        self.logger.debug(
            f"Sending workflow log to Notion: {json.dumps(data, indent=2)}"
        )

        response = requests.post(
            create_page_url, headers=self.headers, data=json.dumps(data)
        )

        if response.status_code == 200:
            self.logger.info(
                f"Workflow run '{workflow_name}' logged to Notion successfully!"
            )
            return response.json()
        else:
            self.logger.error(
                f"Error logging workflow run '{workflow_name}' to Notion: {response.status_code} - {response.text}"
            )
            return None


if __name__ == "__main__":
    load_dotenv()

    # Load Notion config from YAML
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "notion_config.yaml"
    )
    with open(config_path, "r") as f:
        notion_config = yaml.safe_load(f)
    notion_database_id = notion_config["notion_database_id"]
    notion_workflow_database_id = notion_config["notion_workflow_database_id"]

    notion_api_key = os.getenv("NOTION_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    # Get LOG_LEVEL from env, default to WARNING
    log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()

    if (
        not notion_api_key
        or not notion_database_id
        or not gemini_api_key
        or not notion_workflow_database_id
    ):
        raise ValueError(
            "NOTION_API_KEY, and GEMINI_API_KEY must be set in .env file and Notion IDs in config.yaml"
        )

    # Instantiate NotionClient with the determined log level
    notion_client = NotionClient(
        notion_api_key,
        notion_database_id,
        notion_workflow_database_id,
        log_level_str=log_level_str,
    )
    gemini_processor = GeminiProcessor(
        gemini_api_key, log_level_str=log_level_str
    )  # Pass log level to GeminiProcessor as well

    sample_email_body = """
    You sent $1,635.00 to Testing VILLAGE from account ending in (...3925)
 
    Account ending in (...3925)
    Sent on 	Sep 4, 2025 at 4:29 PM ET
    Recipient 	Testing VILLAGE
    Amount 	$1,635.00
    """

    # Replaced print with logger.info
    notion_client.logger.info("Extracting bill information...")
    bill_details = gemini_processor.extract_bill_info(sample_email_body)
    # Use logger.info for the final output, controlled by the log_level
    if bill_details:
        notion_client.logger.info(
            f"Extracted Bill Details: {json.dumps(bill_details.model_dump(), ensure_ascii=False, indent=2)}"
        )
    else:
        notion_client.logger.warning("No bill details extracted.")

    if bill_details:
        # Replaced print with logger.info
        notion_client.logger.info("Adding bill to Notion...")
        notion_client.add_bill_to_notion(bill_details)
    else:
        # Replaced print with logger.warning
        notion_client.logger.warning(
            "No bill details extracted, skipping Notion integration."
        )

    # Example of logging a workflow run
    notion_client.logger.info("Logging a sample workflow run to Notion...")
    notion_client.log_workflow_run(
        workflow_name="Process Bills Workflow",
        status="Success",
        commit_id="a1b2c3d4e5f6",
        duration=120,
        workflow_url="https://github.com/TIMHX/notion-bills-tracker/actions/runs/123456789",
        repository="TIMHX/notion-bills-tracker",
        date="2025-09-06",
        notes="Successfully processed all bills for the day.",
        triggered_by="Manual",
    )
