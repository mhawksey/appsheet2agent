"""
OpenAPI Specification Parser for AppSheet Applications.

Parses AppSheet OpenAPI 3.0 specs (openapi.json) to extract tables,
available actions/endpoints, and column schemas.
"""

import json
from typing import Dict, List, Any, Optional

class AppSheetOpenAPIParser:
    def __init__(self, spec_data: Dict[str, Any]):
        self.spec = spec_data
        self.info = spec_data.get("info", {})
        self.paths = spec_data.get("paths", {})
        self.schemas = spec_data.get("components", {}).get("schemas", {})
        self.servers = spec_data.get("servers", [])

    @classmethod
    def from_file(cls, filepath: str) -> "AppSheetOpenAPIParser":
        with open(filepath, "r", encoding="utf-8") as f:
            return cls(json.load(f))

    @classmethod
    def from_string(cls, content: str) -> "AppSheetOpenAPIParser":
        return cls(json.loads(content))

    def get_app_title(self) -> str:
        return self.info.get("title", "AppSheet App")

    def get_app_id(self) -> str:
        if self.servers:
            url = self.servers[0].get("url", "")
            # Example: https://www.appsheet.com/api/v2/apps/40c823df-3005-4dea-9d32-2197837ce3e7/tables
            if "/apps/" in url:
                parts = url.split("/apps/")[1].split("/")
                return parts[0]
        return ""

    def get_tables(self) -> Dict[str, Dict[str, Any]]:
        """
        Groups API paths by Table Name.
        
        Returns:
            Dict[str, Dict]: Table -> { "actions": [...], "schema_ref": ... }
        """
        tables = {}
        for path, methods in self.paths.items():
            # Example path: "/Facilities/Find" or "/Facilities/View%20Map%20%28Location%29"
            clean_path = path.strip("/")
            parts = clean_path.split("/")
            if len(parts) >= 2:
                table_name = parts[0]
                action_name = parts[1]

                if table_name not in tables:
                    tables[table_name] = {
                        "name": table_name,
                        "actions": [],
                        "schema": self._resolve_table_schema(table_name)
                    }

                tables[table_name]["actions"].append({
                    "path": path,
                    "action": action_name,
                    "summary": methods.get("post", {}).get("summary", "")
                })

        return tables

    def _resolve_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Looks up schema definitions for a given table name."""
        schema_def = self.schemas.get(table_name, {})
        properties = schema_def.get("properties", {})
        required = schema_def.get("required", [])

        columns = {}
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "string")
            enum_values = prop_data.get("enum", [])

            # Detect AppSheet boolean columns represented as string enums (y/yes/true/t/1/no/false/etc.)
            if prop_type == "string" and enum_values:
                bool_indicators = {"true", "false", "yes", "no", "y", "n", "t", "f", "1", "0"}
                if all(str(v).lower() in bool_indicators for v in enum_values):
                    prop_type = "boolean"

            columns[prop_name] = {
                "name": prop_name,
                "type": prop_type,
                "description": prop_data.get("description", ""),
                "required": prop_name in required
            }

        return {
            "name": table_name,
            "columns": columns
        }
