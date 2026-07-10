"""
Antigravity Copilot Engine for Dynamic Agent Authoring & A2UI Card Generation.

Analyzes natural language requests from agent creators, inspects parsed openapi.json
schemas and PDF documentation context, and dynamically constructs:
1. Conversational guidance explanations.
2. Tailored A2UI v0.8 visual cards (Form cards, Record cards, List cards).
3. Generated Google Antigravity SDK @tool Python code.
"""

import json
import os
import re
from typing import Dict, Any, List, Optional

class AntigravityCopilotEngine:
    def __init__(self, parsed_tables: Dict[str, Any], doc_context: str = ""):
        self.tables = parsed_tables or {}
        self.doc_context = doc_context or ""
        self.api_key = os.environ.get("GEMINI_API_KEY", "")

    def process_request(self, user_prompt: str, user_email: str, app_id: str) -> Dict[str, Any]:
        """
        Processes creator prompt (e.g. 'Can I submit an inspection?'),
        matches table & endpoint schemas, and returns guidance, A2UI cards, and tool code.
        """
        prompt_lower = user_prompt.lower()

        # 1. Match Table from Parsed Schema
        matched_table = self._find_matching_table(prompt_lower)
        matched_action = self._find_matching_action(prompt_lower)

        # Retrieve table schema
        if matched_table and matched_table in self.tables:
            table_name = matched_table
        elif self.tables:
            # Fall back to first real parsed table (e.g. Facilities or Inspections)
            table_name = list(self.tables.keys())[0]
        else:
            table_name = "Inspections"

        table_info = self.tables.get(table_name, {})
        columns = table_info.get("schema", {}).get("columns", {})

        # If columns empty, default to common schema fields for table
        if not columns:
            if "inspection" in table_name.lower():
                columns = {
                    "InspectionID": {"type": "string", "required": True},
                    "Facility ID": {"type": "string", "required": True},
                    "Inspection Point ID": {"type": "string", "required": True},
                    "Comments": {"type": "string", "required": False},
                    "Status": {"type": "string", "required": False}
                }
            else:
                columns = {
                    "Facility ID": {"type": "string", "required": True},
                    "Facility Name": {"type": "string", "required": True},
                    "Status": {"type": "string", "required": False}
                }

        # 2. Determine Action & Build A2UI v0.8 Card
        if matched_action == "Add" or any(k in prompt_lower for k in ["submit", "create", "add"]):
            response_text, a2ui_commands = self._build_form_card(table_name, columns, user_email, app_id)
            action_type = "Add"
        elif matched_action == "Edit" or any(k in prompt_lower for k in ["update", "edit", "change"]):
            response_text, a2ui_commands = self._build_form_card(table_name, columns, user_email, app_id, is_edit=True)
            action_type = "Edit"
        else:
            response_text, a2ui_commands = self._build_detail_card(table_name, columns, user_email, app_id)
            action_type = "Find"

        # 3. Generate Antigravity SDK Tool Python Code
        generated_tool_code = self._generate_tool_code(table_name, action_type, columns)

        return {
            "response_text": response_text,
            "a2ui_commands": a2ui_commands,
            "matched_table": table_name,
            "matched_action": action_type,
            "generated_tool_code": generated_tool_code
        }

    def _find_matching_table(self, prompt: str) -> Optional[str]:
        if not self.tables:
            if "inspection" in prompt:
                return "Inspections"
            if "facility" in prompt or "facilities" in prompt:
                return "Facilities"
            if "staff" in prompt:
                return "Staff"
            return None

        for tbl_name in self.tables.keys():
            clean_name = tbl_name.replace("%20", " ").lower()
            if clean_name in prompt or tbl_name.lower() in prompt:
                return tbl_name
            # Singular check (e.g. 'inspection' in 'inspections')
            if len(clean_name) > 3 and clean_name.rstrip("s") in prompt:
                return tbl_name
        return None

    def _find_matching_action(self, prompt: str) -> str:
        if any(w in prompt for w in ["submit", "create", "add", "insert", "new"]):
            return "Add"
        if any(w in prompt for w in ["update", "edit", "modify", "change"]):
            return "Edit"
        if any(w in prompt for w in ["delete", "remove"]):
            return "Delete"
        return "Find"

    def _build_form_card(
        self, 
        table_name: str, 
        columns: Dict[str, Any], 
        user_email: str, 
        app_id: str,
        is_edit: bool = False
    ) -> tuple[str, List[Dict[str, Any]]]:
        clean_table = table_name.replace("%20", " ")
        action_label = "Update" if is_edit else "Submit"
        response_text = (
            f"Yes! You can {action_label.lower()} a record in table '{clean_table}'. "
            f"Here is the dynamic A2UI v0.8 form interface generated for '{clean_table}'. "
            f"All API calls execute under RunAsUserEmail: '{user_email}'."
        )

        col_keys = list(columns.keys())[:6] if columns else ["Facility ID", "Inspection Point ID", "Comments", "Status"]
        
        components = [
            {
                "id": "form_card",
                "component": { "Card": { "child": "form_column" } }
            },
            {
                "id": "form_column",
                "component": {
                    "Column": {
                        "children": {
                            "explicitList": ["form_title", "form_subtitle", *[f"field_{i}" for i in range(len(col_keys))]]
                        }
                    }
                }
            },
            {
                "id": "form_title",
                "component": {
                    "Text": {
                        "text": { "literalString": f"📝 {action_label} {clean_table} Form" },
                        "usageHint": "h3"
                    }
                }
            },
            {
                "id": "form_subtitle",
                "component": {
                    "Text": {
                        "text": { "literalString": f"App ID: {app_id} • User: {user_email}" },
                        "usageHint": "body"
                    }
                }
            }
        ]

        for i, col_name in enumerate(col_keys):
            col_info = columns.get(col_name, {})
            req_str = " (Required)" if isinstance(col_info, dict) and col_info.get("required") else ""
            components.append({
                "id": f"field_{i}",
                "component": {
                    "Text": {
                        "text": { "literalString": f"• {col_name}{req_str}: [ Input Field ]" },
                        "usageHint": "body"
                    }
                }
            })

        a2ui_commands = [
            {
                "beginRendering": {
                    "surfaceId": f"form-{clean_table.lower().replace(' ', '-')}-surface",
                    "root": "form_card"
                }
            },
            {
                "surfaceUpdate": {
                    "surfaceId": f"form-{clean_table.lower().replace(' ', '-')}-surface",
                    "components": components
                }
            }
        ]

        return response_text, a2ui_commands

    def _build_detail_card(
        self, 
        table_name: str, 
        columns: Dict[str, Any], 
        user_email: str, 
        app_id: str
    ) -> tuple[str, List[Dict[str, Any]]]:
        clean_table = table_name.replace("%20", " ")
        response_text = (
            f"Here is the record view for table '{clean_table}'. "
            f"This card queries AppSheet API endpoint '/{table_name}/Find' with RunAsUserEmail: '{user_email}'."
        )

        col_keys = list(columns.keys())[:6] if columns else ["Facility ID", "Name", "Status"]

        components = [
            {
                "id": "detail_card",
                "component": { "Card": { "child": "detail_column" } }
            },
            {
                "id": "detail_column",
                "component": {
                    "Column": {
                        "children": {
                            "explicitList": ["detail_title", *[f"val_{i}" for i in range(len(col_keys))]]
                        }
                    }
                }
            },
            {
                "id": "detail_title",
                "component": {
                    "Text": {
                        "text": { "literalString": f"📋 {clean_table} Details" },
                        "usageHint": "h3"
                    }
                }
            }
        ]

        for i, col_name in enumerate(col_keys):
            components.append({
                "id": f"val_{i}",
                "component": {
                    "Text": {
                        "text": { "literalString": f"• {col_name}: Sample {col_name} Value" },
                        "usageHint": "body"
                    }
                }
            })

        a2ui_commands = [
            {
                "beginRendering": {
                    "surfaceId": f"detail-{clean_table.lower().replace(' ', '-')}-surface",
                    "root": "detail_card"
                }
            },
            {
                "surfaceUpdate": {
                    "surfaceId": f"detail-{clean_table.lower().replace(' ', '-')}-surface",
                    "components": components
                }
            }
        ]

        return response_text, a2ui_commands

    def _generate_tool_code(self, table_name: str, action_type: str, columns: Dict[str, Any]) -> str:
        clean_table = table_name.replace("%20", " ")
        fn_name = f"{action_type.lower()}_{clean_table.lower().replace(' ', '_')}"
        col_list = list(columns.keys())[:4] if columns else ["facility_id"]
        col_args = ", ".join([f"{c.lower().replace(' ', '_')}: str" for c in col_list])

        return f'''from google.antigravity import tool
from appsheet_client import AppSheet

@tool
def {fn_name}(user_email: str, {col_args}) -> dict:
    """
    Executes {action_type} action on AppSheet table '{clean_table}'
    with automatic RunAsUserEmail delegation for user: {{user_email}}.
    """
    client = AppSheet(user_email=user_email)
    payload_row = {{
        {", ".join([f'"{c}": {c.lower().replace(" ", "_")}' for c in col_list])}
    }}
    return client.{action_type.lower()}(table_name="{table_name}", rows=[payload_row])
'''
