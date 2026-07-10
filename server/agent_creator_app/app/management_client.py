"""
Management App API Client (AppSheet2Agent).

Interacts with the AppSheet Management Application (App ID: c61d70ac-1a98-4c36-b735-593f6eeb60b3)
to persist and list agent definitions on behalf of logged-in users via RunAsUserEmail.
Supports LongText column direct JSON text persistence.
"""

import json
from typing import Dict, List, Any, Optional
from app.appsheet_client import AppSheet

MANAGEMENT_APP_ID = "c61d70ac-1a98-4c36-b735-593f6eeb60b3"
MANAGEMENT_ACCESS_KEY = "V2-32Uho-ogHZw-PhFb5-PxefX-pBAis-cJsES-BeiUA-u9IAw"
MANAGEMENT_REGION = "www.appsheet.com"
AGENTS_TABLE = "Agents"

class ManagementAppClient:
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.client = AppSheet(
            app_id=MANAGEMENT_APP_ID,
            access_key=MANAGEMENT_ACCESS_KEY,
            appsheet_region=MANAGEMENT_REGION,
            user_email=user_email
        )

    def list_user_agents(self) -> List[Dict[str, Any]]:
        """
        Queries the 'Agents' table in the Management App for records accessible to user_email.
        Uses RunAsUserEmail to enforce user row-level security.
        """
        result = self.client.find(table_name=AGENTS_TABLE)
        if isinstance(result, list):
            return result
        return result.get("Rows", [])

    def save_agent(
        self,
        app_id: str,
        appsheet_key: str,
        openapi_json_content: str,
        processed_doc_content: str = "",
        configured_capabilities: Optional[List[Dict[str, Any]]] = None,
        status: str = "Draft",
        deployed_url: str = ""
    ) -> Dict[str, Any]:
        """
        Saves or updates an Agent record in the Management App.
        Stores openapi_json_content directly for LongText column types.
        """
        agent_row = {
            "app_id": app_id,
            "appsheet_key": appsheet_key,
            "owner": self.user_email,
            "openapi_json": openapi_json_content,
            "processed_app_definition": processed_doc_content,
            "status": status,
            "deployed_url": deployed_url
        }

        # Try Add action first, fallback to Edit if primary key already exists
        add_result = self.client.add(table_name=AGENTS_TABLE, rows=[agent_row])
        if isinstance(add_result, dict) and "error" in add_result:
            edit_result = self.client.edit(table_name=AGENTS_TABLE, rows=[agent_row])
            return edit_result

        return add_result
