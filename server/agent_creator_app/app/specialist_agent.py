"""
Specialist Agent Architect Engine for 2-Phase Interactive AppSheet Agent Design.
Uses the Google Antigravity SDK to run a stateful, autonomous LLM agent that inspects
schemas and sample data via tools and generates custom A2UI specs.
"""

import json
import os
import re
import urllib.parse
from typing import Dict, Any, List, Optional
import pydantic
from app.compatibility_matrix import COMPATIBILITY_MATRIX

try:
    from google.antigravity import Agent, LocalAgentConfig
    ANTIGRAVITY_SDK_AVAILABLE = True
except ImportError:
    ANTIGRAVITY_SDK_AVAILABLE = False

# 1. Define Pydantic Schema for Antigravity Agent Output
class SpecialistResponseSchema(pydantic.BaseModel):
    response_text: str
    a2ui_commands: List[Dict[str, Any]]
    capabilities: List[Dict[str, Any]]
    is_plan_proposal: bool
    generated_tool_code: Optional[str] = None


class SpecialistAgentArchitect:
    def __init__(
        self, 
        parsed_tables: Dict[str, Any], 
        doc_context: str = "", 
        sample_data: Optional[Dict[str, List[Dict]]] = None,
        region: str = "www.appsheet.com"
    ):
        self.tables = parsed_tables or {}
        self.doc_context = doc_context or ""
        self.sample_data = sample_data or {}
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.gcp_project = os.environ.get("GCP_PROJECT", "")
        
        region_map = {
            "www.appsheet.com": "global",
            "eu.appsheet.com": "eu",
            "asia-southeast.appsheet.com": "asia-southeast1"
        }
        self.gcp_location = region_map.get(region) or os.environ.get("GCP_LOCATION") or "global"

    def generate_greeting(self, app_title: str) -> Dict[str, Any]:
        """
        Generates initial welcome greeting from the Specialist Agent Architect
        when an openapi.json is parsed or loaded.
        """
        table_names = list(self.tables.keys())
        clean_table_names = [t.replace("%20", " ") for t in table_names]

        greeting_text = (
            f"👋 Welcome! I'm your Specialist Agent Architect. I've analyzed your AppSheet app "
            f"('{app_title}').\n\n"
            f"I detected {len(table_names)} data tables:\n"
            + "\n".join([f"• **{name}**" for name in clean_table_names])
            + "\n\nLet's design your Gemini Enterprise AI Agent together!\n\n"
            f"To start: **What data or actions would you like your users to have?**\n"
            f"(For example: *'I would like users to record inspections and query facilities'*)"
        )

        return {
            "response_text": greeting_text,
            "detected_tables": clean_table_names,
            "a2ui_commands": []
        }

    async def process_creator_dialogue(
        self, 
        creator_prompt: str, 
        user_email: str, 
        app_id: str,
        active_capabilities: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes creator input during the design interview. If Antigravity SDK is available,
        it delegates the reasoning loop to a Gemini-powered Agent with dynamic schema-reading tools.
        Otherwise, it falls back to the rule-based simulator.
        """
        use_vertex = bool(self.gcp_project)
        if ANTIGRAVITY_SDK_AVAILABLE and (use_vertex or self.api_key):
            try:
                res = await self._run_antigravity_agent(creator_prompt, user_email, app_id, conversation_id, use_vertex)
                res["routing_mode"] = "Vertex AI LLM Agent"
                res["error_message"] = None
                # Run the response through the sanitization and normalization layer
                res = self._sanitize_agent_response(res, user_email, app_id)
                return res
            except Exception as e:
                err_str = str(e)
                print(f"[SpecialistAgent] Antigravity Agent execution failed: {err_str}. Falling back to simulator.", flush=True)
                res = self._run_rule_based_simulator(creator_prompt, user_email, app_id, active_capabilities)
                res["routing_mode"] = "Rule-Based Simulator Fallback"
                res["error_message"] = f"Antigravity Agent failed: {err_str}"
                return res

        # Graceful fallback to Simulator if credentials are not available
        res = self._run_rule_based_simulator(creator_prompt, user_email, app_id, active_capabilities)
        res["routing_mode"] = "Rule-Based Simulator Fallback"
        res["error_message"] = "Antigravity SDK or GEMINI_API_KEY / GCP_PROJECT not available in environment."
        return res

    async def _run_antigravity_agent(self, prompt: str, user_email: str, app_id: str, conversation_id: Optional[str] = None, use_vertex: bool = False) -> Dict[str, Any]:
        """Runs the stateful Google Antigravity Agent to process chat turns and generate output."""
        save_dir = "/Users/mhawksey/.gemini/antigravity/brain/conversations"
        os.makedirs(save_dir, exist_ok=True)

        # Define tools locally to capture self context
        def get_app_table_schemas() -> Dict[str, Any]:
            """
            Retrieves the schemas for all parsed AppSheet database tables,
            including columns, types, and required properties.
            """
            return self.tables

        def get_sample_rows_for_table(table_name: str) -> List[Dict[str, Any]]:
            """
            Retrieves up to 10 real sample data rows from the AppSheet table
            to understand the actual values and format.
            """
            return self.sample_data.get(table_name, [])

        def search_application_docs(query: str) -> str:
            """
            Searches the uploaded PDF application documentation context for
            business logic rules, requirements, or guidelines.
            """
            return self.doc_context

        # Load A2UI Integration Skill Documentation if available
        a2ui_skill_content = ""
        skill_path = "/Users/mhawksey/Documents/Antigravity Agents/.agents/skills/a2a_a2ui_integration/SKILL.md"
        if not os.path.exists(skill_path):
            skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.agents/skills/a2a_a2ui_integration/SKILL.md"))
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    a2ui_skill_content = f.read()
            except Exception:
                pass

        compatibility_matrix = COMPATIBILITY_MATRIX

        system_instructions = f"""You are the Specialist Agent Architect, an expert AI agent developer.
Your task is to help the creator design a Gemini Enterprise AI Agent for their AppSheet app.
The App ID is '{app_id}' and the user is '{user_email}'.

Core Responsibilities:
1. Greet the user and guide them through designing their agent.
2. Use the get_app_table_schemas tool to see what tables exist in their AppSheet app.
3. Mismatch Checking: If the user asks for a capability or action for a table/concept that does NOT exist in their AppSheet app (e.g. asking to record expenses when the tables are Facilities, Staff, Inspections, Inspection Points), you MUST politely inform them of the mismatch:
   - Tell them which tables are actually available.
   - Explain that you can only design capabilities, forms, and tools for data tables present in their AppSheet database.
   - Do NOT add capabilities for unrelated tables.
4. If they describe what they want to do for a valid table, identify which table and action (Find, Add, Edit, Delete) is needed, and list the capabilities.
5. If they say 'proceed', 'continue', or are ready, propose the final 'Proposed Agent Implementation Plan' (set is_plan_proposal to True).
6. When proposing the plan, you MUST:
   a. Design A2UI v0.8 card commands (beginRendering and surfaceUpdate) for the designed interfaces. 
      Use get_sample_rows_for_table tool to populate realistic preview text. 
      Use native components where appropriate (CheckBox for booleans, TextField with date type for dates, etc.).
   b. Generate custom Python helper tool functions in `generated_tool_code`. Write standard Python code.
   c. Set is_plan_proposal to True.

--- A2A/A2UI v0.8 Integration Skill Reference ---
{a2ui_skill_content}

--- APPSHEET TO A2UI v0.8 COMPATIBILITY MATRIX ---
{compatibility_matrix}

--- STANDARDIZED PYTHON TOOL CODING GUIDELINES ---
When writing python functions in `generated_tool_code`:
1. Decorate every tool function with @tool from vertexai.preview.reasoning_engines.
2. Ensure the function signature accepts user_email: str.
3. You MUST instantiate the standard AppSheet client class: `client = AppSheet(user_email=user_email)`.
4. You MUST NOT use raw `requests.post` calls, construct custom HTTP URLs, or hardcode application access keys. Use the `client.find` and `client.add` wrapper methods.
5. Example of a Find/Query tool:
   ```python
   from vertexai.preview.reasoning_engines import tool
   from appsheet_client import AppSheet

   @tool
   def find_staff_details(user_email: str) -> list:
       \"\"\"
       Fetches all rows from the AppSheet 'Staff' table.
       \"\"\"
       client = AppSheet(user_email=user_email)
       return client.find(table_name="Staff")
   ```
6. Example of an Add/Record tool:
   ```python
   from vertexai.preview.reasoning_engines import tool
   from appsheet_client import AppSheet

   @tool
   def add_staff_member(user_email: str, name: str, email: str, phone: str, shift: str) -> dict:
       \"\"\"
       Adds a new staff member to the 'Staff' table.
       \"\"\"
       client = AppSheet(user_email=user_email)
       new_row = {{
           "Name": name,
           "Email": email,
           "Phone": phone,
           "Shift": shift
       }}
       return client.add(table_name="Staff", rows=[new_row])
   ```

CRITICAL: You MUST write your final response as a JSON block wrapped in triple backticks ```json ... ```. Do NOT write any conversational text outside the JSON block. The JSON MUST match this structure:
{{
  "response_text": "Your conversational text/greeting/reply to the user here.",
  "a2ui_commands": [],
  "capabilities": [],
  "is_plan_proposal": false,
  "generated_tool_code": null
}}
"""
        if use_vertex:
            config = LocalAgentConfig(
                vertex=True,
                project=self.gcp_project,
                location=self.gcp_location,
                model="gemini-3.5-flash",
                app_data_dir=save_dir,
                save_dir=save_dir,
                conversation_id=conversation_id,
                tools=[get_app_table_schemas, get_sample_rows_for_table, search_application_docs],
                system_instructions=system_instructions
            )
        else:
            config = LocalAgentConfig(
                api_key=self.api_key,
                app_data_dir=save_dir,
                save_dir=save_dir,
                conversation_id=conversation_id,
                tools=[get_app_table_schemas, get_sample_rows_for_table, search_application_docs],
                system_instructions=system_instructions
            )

        async with Agent(config=config) as agent:
            response = await agent.chat(prompt)
            text_content = await response.text()
            
            # Extract all JSON blocks using re.findall
            json_blocks = re.findall(r"```json\s*(.*?)\s*```", text_content, re.DOTALL)
            
            data = None
            if json_blocks:
                # Try parsing the blocks in reverse order (most recent/complete first)
                for block in reversed(json_blocks):
                    try:
                        data = json.loads(block.strip())
                        break
                    except Exception:
                        continue
            
            if not data:
                # Try parsing the raw text content as a whole
                try:
                    data = json.loads(text_content.strip())
                except Exception:
                    pass

            if not data:
                print(f"[SpecialistAgent] JSON parse failed on all blocks. Raw response: {text_content}", flush=True)
                raise ValueError(f"Failed to generate structured JSON. Raw text: {text_content}")

            try:
                # Ensure all required keys exist
                for key in ["response_text", "a2ui_commands", "capabilities", "is_plan_proposal"]:
                    if key not in data:
                        if key == "is_plan_proposal":
                            data[key] = False
                        elif key in ("a2ui_commands", "capabilities"):
                            data[key] = []
                        else:
                            data[key] = ""
            except Exception as e:
                raise ValueError(f"Payload validation failed: {e}")

            # Append the conversation ID to return to the client
            data["conversation_id"] = agent.conversation_id
            return data

    def _sanitize_agent_response(self, data: Dict[str, Any], user_email: str, app_id: str) -> Dict[str, Any]:
        """
        Sanitizes and normalizes the parsed LLM agent response to prevent schema hallucinations:
        1. Ensures generated_tool_code is a raw string.
        2. Normalizes capabilities list formatting.
        3. Cleans up environment hallucinations (e.g. default_api calls or raw requests).
        """
        # 1. Sanitize generated_tool_code
        tool_code = data.get("generated_tool_code")
        if isinstance(tool_code, dict):
            tool_code = tool_code.get("tool_code", "") or tool_code.get("code", "")
        
        if not isinstance(tool_code, str):
            tool_code = ""

        # Normalize capabilities first so we can use them for template code generation if needed
        raw_caps = data.get("capabilities", [])
        clean_caps = []
        if isinstance(raw_caps, list):
            for cap in raw_caps:
                if not isinstance(cap, dict):
                    continue
                # Normalize keys: 'method' -> 'action', capitalize action value
                table = cap.get("table") or cap.get("tableName") or "Staff"
                action = cap.get("action") or cap.get("method") or "Find"
                description = cap.get("description") or f"{action} {table} records"
                
                # Clean up casing
                action = action.strip().capitalize()
                if action not in ["Find", "Add", "Edit", "Delete"]:
                    action = "Find"
                    
                clean_caps.append({
                    "table": table,
                    "action": action,
                    "description": description
                })
        data["capabilities"] = clean_caps

        # Check if the LLM hallucinated raw HTTP requests or lacks standard structure
        if tool_code and ("requests" in tool_code or "api.appsheet.com" in tool_code or "YOUR_APPSHEET" in tool_code or "UnboundLocalError" in tool_code):
            print("[SpecialistAgent] Hallucinated/raw HTTP tool code detected. Re-scaffolding clean tool functions from templates.", flush=True)
            tool_code = ""

        if not tool_code and len(clean_caps) > 0:
            scaffolded_tools = []
            for cap in clean_caps:
                table = cap["table"]
                action = cap["action"]
                table_info = self.tables.get(table, {}) or self.tables.get(table.replace(" ", "%20"), {})
                columns = table_info.get("schema", {}).get("columns", {}) if isinstance(table_info, dict) else {}
                if not columns:
                    columns = {
                        "Name": {"type": "string"},
                        "Email": {"type": "string"},
                        "Phone": {"type": "string"}
                    }
                scaffolded_tools.append(self._scaffold_agent_tool(table, action, columns))
            tool_code = "\n\n".join(scaffolded_tools)

        # Remove default_api hallucinations and replace with standard AppSheet client calls
        if tool_code:
            tool_code = re.sub(r"default_api\.appsheet_find", "client.find", tool_code)
            tool_code = re.sub(r"default_api\.appsheet_add", "client.add", tool_code)
            tool_code = re.sub(r"default_api\.[a-zA-Z0-9_]+", "client.find", tool_code)
            
            # Ensure standard imports are present if missing
            if "from appsheet_client import AppSheet" not in tool_code:
                tool_code = "from appsheet_client import AppSheet\n" + tool_code
            
            # Ensure client instantiation is inside the functions
            lines = tool_code.split("\n")
            client_defined = False
            for line in lines:
                if "client = AppSheet" in line:
                    client_defined = True
                    break
            
            if not client_defined:
                for idx, line in enumerate(lines):
                    if "def " in line and ":" in line:
                        indent = len(line) - len(line.lstrip()) + 4
                        lines.insert(idx + 1, " " * indent + f"client = AppSheet(user_email=user_email)")
                        break
                tool_code = "\n".join(lines)
            
        data["generated_tool_code"] = tool_code

        # 3. Sanitize A2UI Commands to match v0.8 components structure
        commands = data.get("a2ui_commands", [])
        if isinstance(commands, list) and len(commands) > 0:
            first_cmd = commands[0]
            if isinstance(first_cmd, dict) and ("command" in first_cmd or "parameters" in first_cmd):
                # Malformed schema detected! Fallback to template A2UI generators for stability
                print("[SpecialistAgent] Malformed A2UI commands schema detected. Re-scaffolding via template.", flush=True)
                new_commands = []
                for cap in clean_caps:
                    raw_table = cap["table"]
                    action = cap["action"]
                    columns = {
                        f"{raw_table} ID": {"type": "string"},
                        "Status": {"type": "string"},
                        "Comments": {"type": "string"}
                    }
                    if action in ["Add", "Edit"]:
                        _, card_cmds = self._evaluate_form_component(raw_table, columns, user_email, app_id)
                    else:
                        _, card_cmds = self._evaluate_view_component(raw_table, columns, user_email, app_id)
                    new_commands.extend(card_cmds)
                data["a2ui_commands"] = new_commands

        return data

    def _run_rule_based_simulator(
        self, 
        creator_prompt: str, 
        user_email: str, 
        app_id: str,
        active_capabilities: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        prompt_lower = creator_prompt.strip().lower()
        capabilities = active_capabilities or []
        
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "help", "who are you", "what can you do"]
        is_greeting = prompt_lower in greetings or len(prompt_lower) <= 3 or prompt_lower.startswith("hello ") or prompt_lower.startswith("hi ")

        clean_table_names = [t.replace("%20", " ") for t in self.tables.keys()] if self.tables else ["Facilities", "Inspections", "Staff"]

        if is_greeting:
            greeting_response = (
                f"Hello! I am your Specialist Agent Architect. I'm here to help you design a custom "
                f"Gemini Enterprise AI Agent for your AppSheet app.\n\n"
                f"Your app contains the following data tables:\n"
                + "\n".join([f"• **{name}**" for name in clean_table_names])
                + "\n\nHow would you like your users to interact with these tables? "
                f"For example, you can tell me:\n"
                f"• *'I would like users to record inspections and query facilities'*\n"
                f"• *'Users should be able to search for staff details'*\n"
                f"• *'Users can update inspection status'*"
            )
            return {
                "response_text": greeting_response,
                "a2ui_commands": [],
                "capabilities": capabilities,
                "is_plan_proposal": False
            }

        plan_triggers = [
            "ready", "propose", "plan", "implementation", "proceed", "continue", 
            "go ahead", "next", "that's all", "done", "yes", "looks good", 
            "no", "ok", "okay", "finish", "sure"
        ]
        is_ready_for_plan = any(t in prompt_lower for t in plan_triggers)

        detected_caps = self._extract_capabilities(prompt_lower)
        for cap in detected_caps:
            if not any(c["table"] == cap["table"] and c["action"] == cap["action"] for c in capabilities):
                capabilities.append(cap)

        # Check if the user prompt mentions any of the actual table names (case-insensitive)
        clean_table_names = [t.replace("%20", " ") for t in self.tables.keys()]
        table_matched = False
        for t in clean_table_names:
            t_lower = t.lower()
            singular = t_lower[:-1] if t_lower.endswith('s') else t_lower
            if t_lower in prompt_lower or (len(singular) > 3 and singular in prompt_lower):
                table_matched = True
                break

        if not capabilities and not is_ready_for_plan:
            if not table_matched:
                mismatch_response = (
                    f"I noticed your request ('{creator_prompt}') doesn't seem to match any of the data tables "
                    f"in your AppSheet application. Your app contains the following tables:\n"
                    + "\n".join([f"• **{name}**" for name in clean_table_names])
                    + "\n\nI can only configure capabilities and generate cards/code for tables present in your application database. "
                    f"Would you like to design actions for one of these tables instead?"
                )
                return {
                    "response_text": mismatch_response,
                    "a2ui_commands": [],
                    "capabilities": [],
                    "is_plan_proposal": False
                }
            else:
                matched_table = next(t for t in clean_table_names if t.lower() in prompt_lower or (len(t.lower()[:-1]) > 3 and t.lower()[:-1] in prompt_lower if t.lower().endswith('s') else False))
                capabilities.append({
                    "table": matched_table,
                    "action": "Add" if any(w in prompt_lower for w in ["record", "submit", "create", "add", "log"]) else "Find",
                    "description": creator_prompt
                })

        if not is_ready_for_plan:
            cap_summary_lines = [f"• **{c['action']} {c['table'].replace('%20', ' ')}** ({'Record/Add' if c['action']=='Add' else 'Query/Find'})" for c in capabilities]
            response_text = (
                f"Great! I have recorded the following capabilities for your agent:\n\n"
                + "\n".join(cap_summary_lines)
                + "\n\nWould you like to add any other capabilities (e.g. updating staff or querying inspection points), "
                f"or are you ready for me to propose the **Full Agent Implementation Plan**? "
                f"(Simply say *'proceed'*, *'continue'*, or *'propose plan'* when ready)."
            )

            return {
                "response_text": response_text,
                "a2ui_commands": [],
                "capabilities": capabilities,
                "is_plan_proposal": False
            }

        return self._generate_implementation_plan_proposal(capabilities, user_email, app_id)

    def _extract_capabilities(self, prompt: str) -> List[Dict[str, Any]]:
        detected = []
        clean_table_names = [t.replace("%20", " ") for t in self.tables.keys()]
        add_keywords = ["record", "submit", "create", "add", "insert", "log", "new", "complete", "write", "post"]
        
        for tbl in clean_table_names:
            tbl_lower = tbl.lower()
            singular = tbl_lower[:-1] if tbl_lower.endswith('s') else tbl_lower
            
            if tbl_lower in prompt or (len(singular) > 3 and singular in prompt):
                action = "Add" if any(w in prompt for w in add_keywords) else "Find"
                detected.append({
                    "table": tbl,
                    "action": action,
                    "description": f"{action} {tbl}"
                })
        return detected

    def _generate_implementation_plan_proposal(
        self, 
        capabilities: List[Dict[str, Any]], 
        user_email: str, 
        app_id: str
    ) -> Dict[str, Any]:
        all_a2ui_commands = []
        all_tool_codes = []
        plan_summary_items = []

        if not capabilities:
            first_table = list(self.tables.keys())[0] if self.tables else "Facilities"
            capabilities = [
                {"table": first_table, "action": "Find", "description": f"Find {first_table}"}
            ]

        for cap in capabilities:
            raw_table = cap["table"]
            clean_table = raw_table.replace("%20", " ")
            action = cap["action"]
            table_info = self.tables.get(raw_table, {}) or self.tables.get(clean_table, {})
            columns = table_info.get("schema", {}).get("columns", {})

            if not columns:
                columns = {
                    f"{clean_table} ID": {"type": "string", "required": True},
                    "Status": {"type": "string", "required": False},
                    "Comments": {"type": "string", "required": False}
                }

            if action in ["Add", "Edit"]:
                _, card_cmds = self._evaluate_form_component(clean_table, columns, user_email, app_id)
            else:
                _, card_cmds = self._evaluate_view_component(clean_table, columns, user_email, app_id)

            all_a2ui_commands.extend(card_cmds)
            tool_code = self._scaffold_agent_tool(clean_table, action, columns)
            all_tool_codes.append(tool_code)

            plan_summary_items.append(f"• **{clean_table} ({action} operation)**: {action} records via `/{clean_table}/{action}` with A2UI Card.")

        response_text = (
            f"📋 **Proposed Agent Implementation Plan**\n\n"
            f"Based on our conversation, here is the complete architecture for your Gemini Enterprise AI Agent:\n\n"
            f"1. **Security & OAuth User Delegation**: All AppSheet API calls automatically enforce `RunAsUserEmail: '{user_email}'`.\n"
            f"2. **Configured Capabilities**:\n"
            + "\n".join(plan_summary_items) + "\n\n"
            f"3. **Evaluated A2UI v0.8 Card Previews**: Rendered below.\n\n"
            f"If this implementation plan looks good, click **Generate Agent & ARD Spec** in Section 2 to download your Cloud Run deployment package!"
        )

        return {
            "response_text": response_text,
            "a2ui_commands": all_a2ui_commands,
            "capabilities": capabilities,
            "generated_tool_code": "\n\n".join(all_tool_codes),
            "is_plan_proposal": True
        }

    def _evaluate_form_component(
        self, 
        table_name: str, 
        columns: Dict[str, Any], 
        user_email: str, 
        app_id: str
    ) -> tuple[str, List[Dict[str, Any]]]:
        col_keys = list(columns.keys())[:5]
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
                        "text": { "literalString": f"📝 Proposed A2UI v0.8 Form: {table_name}" },
                        "usageHint": "h3"
                    }
                }
            },
            {
                "id": "form_subtitle",
                "component": {
                    "Text": {
                        "text": { "literalString": f"App ID: {app_id} • RunAsUserEmail: {user_email}" },
                        "usageHint": "body"
                    }
                }
            }
        ]

        sample_rows = self.sample_data.get(table_name, [])
        sample_row = sample_rows[0] if sample_rows else {}

        for i, col_name in enumerate(col_keys):
            col_info = columns.get(col_name, {})
            req_str = " (Required)" if isinstance(col_info, dict) and col_info.get("required") else ""
            sample_val = sample_row.get(col_name, f"Sample {col_name}")
            
            col_type = col_info.get("type", "string") if isinstance(col_info, dict) else "string"
            input_label = "[ Checkbox Component ]" if col_type == "boolean" else "[ Form Input Component ]"
            
            components.append({
                "id": f"field_{i}",
                "component": {
                    "Text": {
                        "text": { "literalString": f"• {col_name}{req_str}: {input_label} (e.g., {sample_val})" },
                        "usageHint": "body"
                    }
                }
            })

        a2ui_commands = [
            {
                "beginRendering": {
                    "surfaceId": f"form-{table_name.lower().replace(' ', '-')}-surface",
                    "root": "form_card"
                }
            },
            {
                "surfaceUpdate": {
                    "surfaceId": f"form-{table_name.lower().replace(' ', '-')}-surface",
                    "components": components
                }
            }
        ]
        return "Form A2UI Card Evaluated", a2ui_commands

    def _evaluate_view_component(
        self, 
        table_name: str, 
        columns: Dict[str, Any], 
        user_email: str, 
        app_id: str
    ) -> tuple[str, List[Dict[str, Any]]]:
        col_keys = list(columns.keys())[:5]
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
                        "text": { "literalString": f"📋 Proposed A2UI v0.8 View Card: {table_name}" },
                        "usageHint": "h3"
                    }
                }
            }
        ]

        sample_rows = self.sample_data.get(table_name, [])
        sample_row = sample_rows[0] if sample_rows else {}

        for i, col_name in enumerate(col_keys):
            sample_val = sample_row.get(col_name, f"Sample {col_name} Value")
            components.append({
                "id": f"val_{i}",
                "component": {
                    "Text": {
                        "text": { "literalString": f"• {col_name}: {sample_val}" },
                        "usageHint": "body"
                    }
                }
            })

        a2ui_commands = [
            {
                "beginRendering": {
                    "surfaceId": f"detail-{table_name.lower().replace(' ', '-')}-surface",
                    "root": "detail_card"
                }
            },
            {
                "surfaceUpdate": {
                    "surfaceId": f"detail-{table_name.lower().replace(' ', '-')}-surface",
                    "components": components
                }
            }
        ]
        return "View A2UI Card Evaluated", a2ui_commands

    def _scaffold_agent_tool(self, table_name: str, action_type: str, columns: Dict[str, Any]) -> str:
        fn_name = f"{action_type.lower()}_{table_name.lower().replace(' ', '_')}"
        col_list = list(columns.keys())[:4]
        col_args = ", ".join([f"{c.lower().replace(' ', '_')}: str = ''" for c in col_list])

        return f'''# Standard Google Cloud Vertex AI Reasoning Engine Tool Definition
from vertexai.preview.reasoning_engines import tool
from appsheet_client import AppSheet
from auth import auth_token_var, validate_jwt

def get_authenticated_user_email() -> str:
    token = auth_token_var.get().removeprefix("Bearer ").strip()
    if not token:
        raise ValueError("No authorization token present in request context")
    claims = validate_jwt(token)
    return claims.get("email") or claims.get("upn") or claims.get("preferred_username") or ""

@tool
def {fn_name}({col_args}) -> dict:
    """
    Executes {action_type} action on AppSheet table '{table_name}'.
    """
    user_email = get_authenticated_user_email()
    client = AppSheet(user_email=user_email)
    payload_row = {{
        {", ".join([f'"{c}": {c.lower().replace(" ", "_")}' for c in col_list])}
    }}
    return client.{action_type.lower()}(table_name="{table_name}", rows=[payload_row])
'''
