"""
ARD (Agent Registration Definition) Specification & Gemini Enterprise Registration Builder.

Generates:
1. ard.json conforming to https://github.com/ards-project/ard-spec
2. Gemini Enterprise Admin Registration Payload JSON for easy copy-pasting into the admin UI.
"""

import json
import urllib.parse
from typing import Dict, Any, List, Optional

class ARDGenerator:
    def __init__(
        self,
        agent_id: str,
        display_name: str,
        description: str,
        appsheet_app_id: str,
        service_url: str,
        tables: Dict[str, Any],
        version: str = "1.0.0",
        capabilities: Optional[List[Dict[str, Any]]] = None
    ):
        self.agent_id = agent_id or "appsheet-agent"
        self.display_name = display_name or "AppSheet Business Agent"
        self.description = description or "Agent powered by Google Antigravity SDK & AppSheet API"
        self.appsheet_app_id = appsheet_app_id
        self.service_url = service_url.rstrip("/")
        self.tables = tables or {}
        self.version = version
        self.capabilities = capabilities or []

    def generate_ard_spec(self) -> Dict[str, Any]:
        """
        Generates standard ard.json manifest conforming to ARD Specification v1.0.
        """
        capabilities_list = []
        active_tables = {cap["table"] for cap in self.capabilities} if self.capabilities else set()

        for tbl_raw, tbl_data in self.tables.items():
            tbl_clean = urllib.parse.unquote(tbl_raw)
            if self.capabilities and tbl_clean not in active_tables:
                continue
            for act in tbl_data.get("actions", []):
                act_clean = urllib.parse.unquote(act.get("action", "action"))
                
                if self.capabilities:
                    allowed = False
                    for cap in self.capabilities:
                        if cap.get("table") == tbl_clean and cap.get("action", "").lower() == act_clean.lower():
                            allowed = True
                            break
                    if not allowed:
                        continue

                capabilities_list.append({
                    "id": f"{tbl_clean.lower().replace(' ', '_')}_{act_clean.lower().replace(' ', '_')}",
                    "name": f"{act_clean} {tbl_clean}",
                    "description": f"Executes {act_clean} operation on AppSheet table '{tbl_clean}'"
                })

        return {
            "ardVersion": "1.0",
            "agent": {
                "id": self.agent_id,
                "name": self.display_name,
                "description": self.description,
                "version": self.version,
                "publisher": "Organization Agent Creator",
                "iconUrl": "https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/png/128/emoji_u1f4ca.png"
            },
            "transport": {
                "protocol": "A2A_JSON_RPC",
                "endpoint": f"{self.service_url}/a2a"
            },
            "authentication": {
                "type": "OAUTH2_BEARER",
                "scopes": ["openid", "email", "profile"],
                "delegationProperty": "RunAsUserEmail"
            },
            "extensions": [
                {
                    "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8",
                    "description": "A2UI v0.8 visual card rendering extension",
                    "catalogUrl": "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
                }
            ],
            "capabilities": capabilities_list
        }

    def generate_gemini_enterprise_admin_payload(self) -> Dict[str, Any]:
        """
        Generates the standard A2A v0.3.0 compliant AgentCard JSON payload
        required by Gemini Enterprise registry to register the custom agent.
        """
        skills = []
        active_tables = {cap["table"] for cap in self.capabilities} if self.capabilities else set(self.tables.keys())

        for tbl in self.tables.keys():
            tbl_clean = urllib.parse.unquote(tbl)
            if tbl_clean not in active_tables:
                continue
            skills.append({
                "id": tbl_clean.lower().replace(" ", "_"),
                "name": f"{tbl_clean} management",
                "description": f"Query and update data in the AppSheet '{tbl_clean}' table.",
                "examples": [f"show {tbl_clean.lower()}", f"find {tbl_clean.lower()}"],
                "tags": [tbl_clean.lower().replace(" ", "_")]
            })
            
        return {
            "name": self.agent_id,
            "description": f"{self.description} (App ID: {self.appsheet_app_id})",
            "url": self.service_url,
            "version": "1.0.0",
            "protocolVersion": "0.3.0",
            "preferredTransport": "JSONRPC",
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "supportsAuthenticatedExtendedCard": True,
            "iconUrl": "https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/png/128/emoji_u1f4ca.png",
            "capabilities": {
                "streaming": False,
                "extensions": [
                    {
                        "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8",
                        "description": "Ability to render A2UI cards",
                        "required": False,
                        "params": {
                            "supportedCatalogIds": [
                                "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
                            ]
                        }
                    }
                ]
            },
            "skills": skills
        }
