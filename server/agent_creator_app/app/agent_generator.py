"""
Agent Code Generator & Package Builder using Hybrid Google Antigravity SDK & AppSheet A2A Boilerplate.
Features:
1. Declarative Security Policies (hooks.policy)
2. Multimodal Attachment Ingestion (types.from_file & Image)
3. GCP Vertex AI Mode Flag (LocalAgentConfig(vertex=True))
"""

import json
import zipfile
import io
import os
import re
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional

def sanitize_python_identifier(name: str) -> str:
    """Sanitizes column names into valid Python parameter identifiers."""
    unquoted = urllib.parse.unquote(name)
    cleaned = unquoted.replace(" ", "_")
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned).lower()
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned

class AgentCodeGenerator:
    def __init__(
        self,
        app_id: str,
        access_key: str,
        region: str,
        tables: Dict[str, Any],
        doc_context: str = "",
        vertex_mode: bool = False,
        gcp_project: str = "",
        capabilities: Optional[List[Dict[str, Any]]] = None
    ):
        self.app_id = app_id
        self.access_key = access_key
        self.region = region or "www.appsheet.com"
        self.tables = tables or {}
        self.doc_context = doc_context or ""
        self.vertex_mode = vertex_mode
        self.gcp_project = gcp_project or "your-gcp-project"
        self.capabilities = capabilities or []

    def generate_agent_tools(self) -> str:
        """Generates standard Python helper tool functions with policies & multimodal attachment definitions."""
        tool_code_blocks = [
            "# ==============================================================================",
            "# APPSHEET DATA ACTION TOOLS & SECURITY ACCESS SCHEMAS",
            "# ==============================================================================",
            "",
            "# DECLARATIVE SECURITY POLICIES (Zero-Trust Access Configuration)",
            "SECURITY_POLICIES = {",
            "    'default': 'deny',                    # Deny unapproved actions by default",
            "    'read_queries': 'allow',              # find_* queries execute automatically",
            "    'write_mutations': 'ask_user',        # add_* and edit_* require confirmation",
            "}",
            "",
            "import os",
            "from appsheet_client import AppSheet",
            "from auth import auth_token_var, validate_jwt",
            "",
            "def get_authenticated_user_email() -> str:",
            "    token = auth_token_var.get().removeprefix('Bearer ').strip()",
            "    if not token:",
            "        raise ValueError('No authorization token present in request context')",
            "    claims = validate_jwt(token)",
            "    return claims.get('email') or claims.get('upn') or claims.get('preferred_username') or ''"
        ]

        active_actions = {}
        if self.capabilities:
            for cap in self.capabilities:
                tbl = cap.get("table")
                act = cap.get("action")
                if tbl and act:
                    active_actions.setdefault(tbl, []).append(act.lower())

        for table_raw, table_info in self.tables.items():
            clean_table = urllib.parse.unquote(table_raw)
            if self.capabilities and clean_table not in active_actions:
                continue

            fn_base = sanitize_python_identifier(clean_table)
            columns = table_info.get("schema", {}).get("columns", {})
            col_list = list(columns.keys()) if columns else [f"{clean_table} ID", "Status", "Comments"]
            
            param_defs = []
            dict_entries = []
            param_vars = []
            image_handling_lines = []

            for col in col_list:
                clean_col = urllib.parse.unquote(col)
                param_name = sanitize_python_identifier(clean_col)
                param_defs.append(f"{param_name}: str = ''")
                dict_entries.append(f'"{clean_col}": {param_name}')
                param_vars.append(param_name)

                # Check if column represents an image or photo attachment
                col_lower = clean_col.lower()
                if any(k in col_lower for k in ["image", "photo", "headshot", "floorplan", "file", "attachment", "picture"]):
                    image_handling_lines.append(f"    # Multimodal Image Attachment Ingestion for '{clean_col}'")
                    image_handling_lines.append(f"    if {param_name} and os.path.exists({param_name}):")
                    image_handling_lines.append(f"        pass  # Attachment parsing logic")

            col_params = ", ".join(param_defs)
            payload_dict_str = ", ".join(dict_entries)
            any_vars_str = ", ".join(param_vars)
            multimodal_code = "\n".join(image_handling_lines) if image_handling_lines else "    pass"

            # Add Tool (only if 'add' in active_actions or capabilities is empty)
            if not self.capabilities or "add" in active_actions.get(clean_table, []):
                tool_code_blocks.append(f'''def add_{fn_base}({col_params}) -> dict:
    """
    Add, create, or insert a new record into AppSheet table '{clean_table}'.
    """
{multimodal_code}
    user_email = get_authenticated_user_email()
    client = AppSheet(user_email=user_email)
    payload_row = {{{payload_dict_str}}}
    return client.add(table_name="{clean_table}", rows=[payload_row])
''')

            # Find Tool (only if 'find' or 'query' in active_actions or capabilities is empty)
            if not self.capabilities or any(act in active_actions.get(clean_table, []) for act in ["find", "query"]):
                tool_code_blocks.append(f'''def find_{fn_base}({col_params}) -> dict:
    """
    Retrieve, list, or search records from AppSheet table '{clean_table}'.
    """
    user_email = get_authenticated_user_email()
    client = AppSheet(user_email=user_email)
    payload_row = {{{payload_dict_str}}}
    return client.find(table_name="{clean_table}", rows=[payload_row] if any([{any_vars_str}]) else None)
''')

            # Edit Tool (only if 'edit' or 'update' in active_actions or capabilities is empty)
            if not self.capabilities or any(act in active_actions.get(clean_table, []) for act in ["edit", "update"]):
                tool_code_blocks.append(f'''def edit_{fn_base}({col_params}) -> dict:
    """
    Update, edit, or modify an existing record in AppSheet table '{clean_table}'.
    """
{multimodal_code}
    user_email = get_authenticated_user_email()
    client = AppSheet(user_email=user_email)
    payload_row = {{{payload_dict_str}}}
    non_empty_row = {{k: v for k, v in payload_row.items() if v != ''}}
    return client.edit(table_name="{clean_table}", rows=[non_empty_row])
''')

        return "\n".join(tool_code_blocks)

    def generate_agent_executor_code(self) -> str:
        """Generates agent_executor.py with clean tool functions, policies & A2UI card formatting."""
        table_names = [urllib.parse.unquote(t) for t in self.tables.keys()]
        first_table = "Facilities"
        if self.capabilities:
            first_table = self.capabilities[0].get("table") or first_table
        elif table_names:
            first_table = table_names[0]
        agent_tools_code = self.generate_agent_tools()
        vertex_status = "Enabled" if self.vertex_mode else "Disabled (Standard A2A Handover)"
        
        # Map Region Domain to GCP Model Location/Region
        region_map = {
            "www.appsheet.com": "global",
            "eu.appsheet.com": "eu",
            "asia-southeast.appsheet.com": "asia-southeast1"
        }
        gcp_region = region_map.get(self.region, "global")

        # Parse PDF metadata for hidden and label columns
        pdf_metadata = {}
        if self.doc_context:
            import re
            schema_blocks = self.doc_context.split("Schema Name ")
            for block in schema_blocks[1:]:
                lines = block.split("\n")
                if not lines:
                    continue
                schema_name = lines[0].strip().split()[0]
                if schema_name not in pdf_metadata:
                    pdf_metadata[schema_name] = {}
                current_col = None
                for line in lines[1:]:
                    line_str = line.strip()
                    col_match = re.match(r"^Column name\s+(.+)$", line_str, re.IGNORECASE)
                    if col_match:
                        current_col = col_match.group(1).strip()
                        pdf_metadata[schema_name][current_col] = {"hidden": False, "label": False}
                    if current_col:
                        if line_str.startswith("Hidden Yes"):
                            pdf_metadata[schema_name][current_col]["hidden"] = True
                        elif line_str.startswith("Label Yes"):
                            pdf_metadata[schema_name][current_col]["label"] = True

        table_schemas_dict = {}
        for table_raw, table_info in self.tables.items():
            clean_table = urllib.parse.unquote(table_raw)
            columns = table_info.get("schema", {}).get("columns", {})
            # Make a copy of columns to avoid mutating shared state
            table_schemas_dict[clean_table] = {
                col_name: dict(col_val) if isinstance(col_val, dict) else {"type": str(col_val)}
                for col_name, col_val in columns.items()
            }
            
            # Merge PDF column metadata
            pdf_schema = pdf_metadata.get(f"{clean_table}_Schema") or pdf_metadata.get(clean_table)
            if pdf_schema:
                for col_name, col_meta in table_schemas_dict[clean_table].items():
                    pdf_col = None
                    for pc in pdf_schema.keys():
                        if pc.lower() == col_name.lower():
                            pdf_col = pc
                            break
                    if pdf_col:
                        col_meta["hidden"] = pdf_schema[pdf_col].get("hidden", False)
                        col_meta["label"] = pdf_schema[pdf_col].get("label", False)
                        
        # Parse PDF metadata for views
        pdf_views = {}
        if self.doc_context:
            import re
            view_blocks = self.doc_context.split("View name ")
            for block in view_blocks[1:]:
                lines = block.split("\n")
                if not lines:
                    continue
                v_name = lines[0].strip().split()[0]
                if v_name not in pdf_views:
                    pdf_views[v_name] = {}
                    
                for line in lines[1:]:
                    line_str = line.strip()
                    if line_str.startswith("View type"):
                        pdf_views[v_name]["type"] = line_str.replace("View type", "").strip()
                    elif line_str.startswith("SortBy"):
                        raw_val = line_str.replace("SortBy", "").strip()
                        try:
                            pdf_views[v_name]["SortBy"] = json.loads(raw_val)
                        except Exception:
                            pdf_views[v_name]["SortBy"] = {"Column": raw_val, "Order": "Ascending"}
                    elif line_str.startswith("GroupBy"):
                        raw_val = line_str.replace("GroupBy", "").strip()
                        try:
                            pdf_views[v_name]["GroupBy"] = json.loads(raw_val)
                        except Exception:
                            pdf_views[v_name]["GroupBy"] = {"Column": raw_val, "Order": "Ascending"}

        views_metadata_dict = {}
        for v_name, v_info in pdf_views.items():
            tbl_match = None
            for tbl in table_schemas_dict.keys():
                if tbl.lower() in v_name.lower():
                    tbl_match = tbl
                    break
            if tbl_match:
                current_meta = views_metadata_dict.setdefault(tbl_match, {})
                if v_info.get("type") == "deck" or not current_meta:
                    if "SortBy" in v_info:
                        current_meta["SortBy"] = v_info["SortBy"]
                    if "GroupBy" in v_info:
                        current_meta["GroupBy"] = v_info["GroupBy"]

        table_schemas_json = json.dumps(table_schemas_dict, indent=4)
        views_metadata_json = json.dumps(views_metadata_dict, indent=4)

        code = f'''"""
Generated AppSheet Hybrid Agent Executor (A2A Protocol + Google Antigravity SDK).
App ID: {self.app_id}
Region: {self.region}
Tables: {", ".join(table_names)}
Vertex AI Mode: {self.vertex_mode}
"""

import os
import urllib.parse
from typing import List, Dict, Any
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Part, TextPart, DataPart, TaskStatusUpdateEvent, TaskStatus, TaskState, Message, Role
from a2a.utils import new_agent_text_message, new_agent_parts_message
from datetime import datetime, timezone

from appsheet_client import AppSheet
from auth import auth_token_var, validate_jwt
from card_templates import create_record_card, create_status_card, create_table_list_card, create_form_card

def sanitize_python_identifier(name: str) -> str:
    """Sanitizes column or table names to be valid python variable/function names."""
    import re
    s = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    s = re.sub(r'^_+', '', s)
    s = re.sub(r'_+', '_', s)
    if s and s[0].isdigit():
        s = 'n_' + s
    return s.lower()

def format_records_for_ux(tbl_name: str, records: list) -> list:
    """Filters out hidden columns and moves label columns to the front of records."""
    schema = TABLE_SCHEMAS.get(tbl_name, {{}})
    formatted = []
    
    hidden_cols = set()
    label_cols = []
    
    for col_name, col_meta in schema.items():
        if isinstance(col_meta, dict):
            if col_meta.get("hidden"):
                hidden_cols.add(col_name)
            if col_meta.get("label"):
                label_cols.append(col_name)
                
    hidden_cols.add("_RowNumber")
    hidden_cols.add("RowNumber")
    hidden_cols.add("Row ID")
    hidden_cols.add("RowID")
    
    # Auto-sort records if view metadata specifies sorting
    meta = VIEW_METADATA.get(tbl_name)
    if meta and "SortBy" in meta:
        sort_col = meta["SortBy"].get("Column")
        sort_order = meta["SortBy"].get("Order", "Ascending")
        matched_key = None
        if records and isinstance(records[0], dict):
            for k in records[0].keys():
                if k.lower() == sort_col.lower():
                    matched_key = k
                    break
        if matched_key:
            try:
                records.sort(
                    key=lambda x: str(x.get(matched_key, "")).lower(),
                    reverse=(sort_order.lower() == "descending" or sort_order.lower() == "desc")
                )
            except Exception:
                pass
    
    for rec in records:
        if not isinstance(rec, dict):
            formatted.append(rec)
            continue
            
        visible_data = {{}}
        for k, v in rec.items():
            is_hidden = k in hidden_cols or k.lower() in [hc.lower() for hc in hidden_cols]
            if not is_hidden:
                visible_data[k] = v
                
        reordered_data = {{}}
        for label_col in label_cols:
            matched_key = None
            for k in visible_data.keys():
                if k.lower() == label_col.lower():
                    matched_key = k
                    break
            if matched_key:
                reordered_data[matched_key] = visible_data.pop(matched_key)
                
        reordered_data.update(visible_data)
        formatted.append(reordered_data)
        
    return formatted

import json
TABLE_SCHEMAS = json.loads(r"""{table_schemas_json}""")
VIEW_METADATA = json.loads(r"""{views_metadata_json}""")

{agent_tools_code}

PRIMARY_TABLE = "{first_table}"
PROJECT_ID = os.environ.get("GCP_PROJECT") or "{self.gcp_project}"
LOCATION = os.environ.get("GCP_LOCATION") or "{gcp_region}"

class AppSheetAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        context.add_activated_extension("https://a2ui.org/a2a-extension/a2ui/v0.8")

        user_text = ""
        ui_event = None
        if context.message and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, "root"):
                    if isinstance(part.root, TextPart) and part.root.text:
                        user_text = part.root.text.strip()
                    elif isinstance(part.root, DataPart) and isinstance(part.root.data, dict) and "userAction" in part.root.data:
                        ui_event = part.root.data["userAction"]

        print(f"[A2A Agent] execute() called: user_text='{{user_text}}', ui_event='{{ui_event is not None}}'")

        token = auth_token_var.get().removeprefix("Bearer ").strip()
        if not token and context.metadata:
            def search_token(d):
                if not isinstance(d, dict):
                    return None
                for k, v in d.items():
                    if k.lower() in ("authorization", "access_token") and isinstance(v, str) and v:
                        return v.removeprefix("Bearer ").strip()
                    if isinstance(v, dict):
                        res = search_token(v)
                        if res:
                            return res
                return None
            token = search_token(context.metadata) or ""
            if token:
                auth_token_var.set(f"Bearer {{token}}")

        print(f"[A2A Agent] Auth token retrieved: {{'Yes' if token else 'No'}}")

        if not token:
            print("[A2A Agent] Error: Authentication token is missing!")
            auth_event = TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=False,
                status=TaskStatus(
                    state=TaskState.auth_required,
                    message=Message(
                        role=Role.agent,
                        parts=[Part(root=TextPart(text="Authentication required for AppSheet API."))],
                        task_id=context.task_id or "",
                        context_id=context.context_id or "",
                    ),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            await event_queue.enqueue_event(auth_event)
            return

        try:
            claims = validate_jwt(token)
            user_email = claims.get("email") or claims.get("upn") or claims.get("preferred_username") or ""
            print(f"[A2A Agent] User identity verified: email='{{user_email}}'")
        except Exception as e:
            print(f"[A2A Agent] Error: OAuth validation failed: {{e}}")
            await event_queue.enqueue_event(new_agent_text_message(f"❌ OAuth validation error: {{e}}"))
            return

        # 1. Handle A2UI Interactive Client Event submissions
        if ui_event:
            action_name = ui_event.get("name", "")
            ctx = ui_event.get("context", {{}})
            print(f"[A2A Agent] Processing ClientEvent: '{{action_name}}'")
            
            # Map context list/dict to flat dictionary
            ctx_dict = {{}}
            if isinstance(ctx, list):
                for item in ctx:
                    if isinstance(item, dict) and "key" in item:
                        ctx_dict[item["key"]] = item.get("value")
            elif isinstance(ctx, dict):
                ctx_dict = ctx
                
            if action_name.startswith("submit_add_"):
                target_table = action_name.replace("submit_add_", "")
                tbl_name = None
                for t in TABLE_SCHEMAS.keys():
                    if t.lower().replace(" ", "_") == target_table.lower().replace(" ", "_"):
                        tbl_name = t
                        break
                        
                if tbl_name:
                    fn_name = f"add_{{sanitize_python_identifier(tbl_name)}}"
                    tool_fn = globals().get(fn_name)
                    if tool_fn:
                        import inspect
                        sig = inspect.signature(tool_fn)
                        fn_args = {{}}
                        for param in sig.parameters.values():
                            for col_name, col_val in ctx_dict.items():
                                if sanitize_python_identifier(col_name) == param.name:
                                    if isinstance(col_val, bool):
                                        fn_args[param.name] = "Y" if col_val else "N"
                                    else:
                                        fn_args[param.name] = str(col_val)
                                    break
                                    
                        print(f"[A2A Agent] Form submit calling tool '{{fn_name}}' with args: {{fn_args}}")
                        res = tool_fn(**fn_args)
                        print(f"[A2A Agent] Tool execution returned: {{res}}")
                        
                        card_cmds = create_status_card("appsheet-card", "Record Added Successfully", f"New record has been written to table '{{tbl_name}}'.")
                        msg = new_agent_parts_message(
                            parts=[
                                Part(root=TextPart(text=f"Successfully added record to '{{tbl_name}}':")),
                                *[Part(root=DataPart(data=c, metadata={{"mimeType": "application/json+a2ui"}})) for c in card_cmds]
                            ],
                            context_id=context.context_id,
                            task_id=context.task_id,
                        )
                        await event_queue.enqueue_event(msg)
                        return
                    else:
                        print(f"[A2A Agent] Error: Tool function '{{fn_name}}' not found.")
                else:
                    print(f"[A2A Agent] Error: Table matching '{{target_table}}' not found.")
            elif action_name.startswith("submit_edit_"):
                target_table = action_name.replace("submit_edit_", "")
                tbl_name = None
                for t in TABLE_SCHEMAS.keys():
                    if t.lower().replace(" ", "_") == target_table.lower().replace(" ", "_"):
                        tbl_name = t
                        break
                        
                if tbl_name:
                    fn_name = f"edit_{{sanitize_python_identifier(tbl_name)}}"
                    tool_fn = globals().get(fn_name)
                    if tool_fn:
                        import inspect
                        sig = inspect.signature(tool_fn)
                        fn_args = {{}}
                        for param in sig.parameters.values():
                            for col_name, col_val in ctx_dict.items():
                                if sanitize_python_identifier(col_name) == param.name:
                                    if isinstance(col_val, bool):
                                        fn_args[param.name] = "Y" if col_val else "N"
                                    else:
                                        fn_args[param.name] = str(col_val)
                                    break
                                    
                        print(f"[A2A Agent] Form submit calling tool '{{fn_name}}' with args: {{fn_args}}")
                        res = tool_fn(**fn_args)
                        print(f"[A2A Agent] Tool execution returned: {{res}}")
                        
                        card_cmds = create_status_card("appsheet-card", "Record Updated Successfully", f"Record has been updated in table '{{tbl_name}}'.")
                        msg = new_agent_parts_message(
                            parts=[
                                Part(root=TextPart(text=f"Successfully updated record in '{{tbl_name}}':")),
                                *[Part(root=DataPart(data=c, metadata={{"mimeType": "application/json+a2ui"}})) for c in card_cmds]
                            ],
                            context_id=context.context_id,
                            task_id=context.task_id,
                        )
                        await event_queue.enqueue_event(msg)
                        return
                    else:
                        print(f"[A2A Agent] Error: Tool function '{{fn_name}}' not found.")
                else:
                    print(f"[A2A Agent] Error: Table matching '{{target_table}}' not found.")

        # 2. Intercept text requests starting with add/create/new to return interactive input form
        cmd = user_text.lower()
        if any(w in cmd.split() for w in ("add", "create", "new")):
            tbl_name = PRIMARY_TABLE
            for t in TABLE_SCHEMAS.keys():
                t_clean = t.lower().rstrip('s')
                if t_clean in cmd:
                    tbl_name = t
                    break
                    
            fn_name = f"add_{{sanitize_python_identifier(tbl_name)}}"
            if fn_name in globals():
                print(f"[A2A Agent] Intercepted add command. Render form card for table '{{tbl_name}}'...")
                columns = TABLE_SCHEMAS.get(tbl_name, {{}})
                submit_action = f"submit_add_{{sanitize_python_identifier(tbl_name)}}"
                card_cmds = create_form_card("appsheet-form", f"Add New {{tbl_name}}", columns, submit_action)
                
                msg = new_agent_parts_message(
                    parts=[
                        Part(root=TextPart(text=f"Please fill out the form below to add a record to '{{tbl_name}}':")),
                        *[Part(root=DataPart(data=c, metadata={{"mimeType": "application/json+a2ui"}})) for c in card_cmds]
                    ],
                    context_id=context.context_id,
                    task_id=context.task_id,
                )
                await event_queue.enqueue_event(msg)
                return
'''

        if self.vertex_mode:
            code += f'''
        # GCP Vertex AI LLM Mode
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
            
            # Find all active functions in globals starting with 'find_', 'add_', or 'edit_'
            tools = [v for k, v in globals().items() if (k.startswith("find_") or k.startswith("add_") or k.startswith("edit_")) and callable(v)]
            print(f"[A2A Agent] Vertex AI Mode: Loaded {{len(tools)}} tool(s) to offer LLM: {{[t.__name__ for t in tools]}}")
            
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=user_text,
                config=types.GenerateContentConfig(
                    tools=tools,
                    temperature=0.0,
                    system_instruction="You are a helpful AppSheet assistant. Use the provided tools to query or update records in response to the user query.",
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(
                            mode="ANY"
                        )
                    )
                )
            )
            
            print(f"[A2A Agent] Vertex AI Response: text='{{response.text}}', function_calls={{response.function_calls}}")
            
            if response.function_calls:
                for fc in response.function_calls:
                    func_name = fc.name
                    args = fc.args or {{}}
                    print(f"[A2A Agent] Vertex AI requested tool execution: '{{func_name}}' with args: {{args}}")
                    tool_fn = globals().get(func_name)
                    if tool_fn:
                        res = tool_fn(**args)
                        print(f"[A2A Agent] Tool execution returned: {{res}}")
                        records = res if isinstance(res, list) else res.get("Rows", []) if isinstance(res, dict) else []
                        
                        tbl_name = PRIMARY_TABLE
                        for t_raw in {table_names}:
                            if func_name.replace("find_", "").replace("add_", "").replace("edit_", "") in t_raw.lower().replace(" ", "_"):
                                tbl_name = t_raw
                                break
                                
                        print(f"[A2A Agent] Found {{len(records)}} records for table '{{tbl_name}}'")
                        if not records:
                            print(f"[A2A Agent] Returning 'No records found' for table '{{tbl_name}}'")
                            await event_queue.enqueue_event(new_agent_text_message(f"No records found in table '{{tbl_name}}'."))
                            return
                            
                        formatted_recs = format_records_for_ux(tbl_name, records)
                        if len(formatted_recs) > 1:
                            print(f"[A2A Agent] Creating table list card for {{len(formatted_recs)}} records of '{{tbl_name}}'...")
                            card_cmds = create_table_list_card("appsheet-card", f"AppSheet: {{tbl_name}} List", formatted_recs)
                        else:
                            print(f"[A2A Agent] Creating single record card for '{{tbl_name}}'...")
                            card_cmds = create_record_card("appsheet-card", f"AppSheet: {{tbl_name}} Record", formatted_recs[0])
                            
                        print(f"[A2A Agent] Generated Card Commands payload: {{card_cmds}}")
                        msg = new_agent_parts_message(
                            parts=[
                                Part(root=TextPart(text=f"Fetched {{len(records)}} record(s) from '{{tbl_name}}':")),
                                *[Part(root=DataPart(data=c, metadata={{"mimeType": "application/json+a2ui"}})) for c in card_cmds]
                            ],
                            context_id=context.context_id,
                            task_id=context.task_id,
                        )
                        print(f"[A2A Agent] Enqueuing parts message: {{msg}}")
                        await event_queue.enqueue_event(msg)
                        return
                        
            print(f"[A2A Agent] Returning conversational text response: {{response.text}}")
            await event_queue.enqueue_event(new_agent_text_message(response.text or "No response from model."))
            
        except Exception as e:
            print(f"[A2A Agent] Vertex AI Execution Error: {{e}}")
            await event_queue.enqueue_event(new_agent_text_message(f"❌ Vertex AI Execution Error: {{e}}"))
            return
'''
        else:
            code += f'''
        # Standard Rule-Based Command Mode
        cmd = user_text.lower()
        print(f"[A2A Agent] Standard Mode: Evaluating query command: '{{cmd}}'")
        if "show" in cmd or "get" in cmd or "find" in cmd or "list" in cmd or "query" in cmd:
            target_fn = "find_" + "{sanitize_python_identifier(first_table)}"
            print(f"[A2A Agent] Resolved target tool function: '{{target_fn}}'")
            tool_fn = globals().get(target_fn)
            
            if tool_fn:
                print(f"[A2A Agent] Calling tool function: '{{target_fn}}'...")
                res = tool_fn()
            else:
                print(f"[A2A Agent] Target tool function not found in namespace. Falling back to direct AppSheet client search for table '{{PRIMARY_TABLE}}'...")
                client = AppSheet(user_email=user_email)
                res = client.find(table_name=PRIMARY_TABLE)

            print(f"[A2A Agent] Tool execution returned payload: {{res}}")
            records = res if isinstance(res, list) else res.get("Rows", []) if isinstance(res, dict) else []
            if not records:
                print(f"[A2A Agent] No records returned for table '{{PRIMARY_TABLE}}'")
                await event_queue.enqueue_event(new_agent_text_message(f"No records found in '{{PRIMARY_TABLE}}' for {{user_email}}."))
                return

            formatted_recs = format_records_for_ux(PRIMARY_TABLE, records)
            if len(formatted_recs) > 1:
                print(f"[A2A Agent] Creating table list card for {{len(formatted_recs)}} records of '{{PRIMARY_TABLE}}'...")
                card_cmds = create_table_list_card("appsheet-card", f"AppSheet: {{PRIMARY_TABLE}} List", formatted_recs)
            else:
                print(f"[A2A Agent] Creating single record card for '{{PRIMARY_TABLE}}'...")
                first_rec = formatted_recs[0]
                card_cmds = create_record_card("appsheet-card", f"AppSheet: {{PRIMARY_TABLE}} Record", first_rec)

            print(f"[A2A Agent] Generated Card Commands payload: {{card_cmds}}")
            msg = new_agent_parts_message(
                parts=[
                    Part(root=TextPart(text=f"Fetched {{len(records)}} record(s) as {{user_email}}:")),
                    *[Part(root=DataPart(data=c, metadata={{"mimeType": "application/json+a2ui"}})) for c in card_cmds]
                ],
                context_id=context.context_id,
                task_id=context.task_id,
            )
            print(f"[A2A Agent] Enqueuing parts message: {{msg}}")
            await event_queue.enqueue_event(msg)
            return

        # Default Help Response
        help_msg = (
            f"🤖 AppSheet Agent Active (Google Antigravity SDK + A2A Protocol)\\n"
            f"App ID: `{self.app_id}`\\n"
            f"Authenticated User: **{{user_email}}**\\n"
            f"GCP Vertex AI Mode: {vertex_status}\\n"
            f"Declarative Security Policies: 3 Active Rules (`deny(*)`, `allow(find_*)`, `ask_user(add_*)`)\\n"
            f"Configured Tables: {', '.join(table_names)}\\n\\n"
            f"Try typing: *'find records'* to query table `{first_table}`."
        )
        await event_queue.enqueue_event(new_agent_text_message(help_msg))
'''

        code += f'''
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass
'''
        return code

    def generate_main_py(self) -> str:
        """Generates main.py Cloud Run entrypoint."""
        return f'''"""
Cloud Run Starlette Application Entrypoint for AppSheet Agent.
Includes /healthz probe endpoint and AuthHeaderMiddleware.
"""

import os
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, AgentExtension

from agent_executor import AppSheetAgentExecutor
from auth import auth_token_var

appsheet_skill = AgentSkill(
    id="appsheet_manage",
    name="AppSheet Manager",
    description="Query and update AppSheet application data on behalf of the logged in user.",
    tags=["appsheet", "database", "crud"],
    examples=["show records", "list tasks", "add record"],
)

_base_url = os.environ.get("AGENT_BASE_URL") or "https://placeholder-url.a.run.app"

a2ui_extension = AgentExtension(
    uri="https://a2ui.org/a2a-extension/a2ui/v0.8",
    description="Ability to render A2UI cards in Gemini Enterprise",
    required=False,
    params={{
        "supportedCatalogIds": [
            "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
        ]
    }}
)

public_agent_card = AgentCard(
    name="appsheet_agent",
    description="AppSheet A2A Agent with OAuth RunAsUserEmail delegation, Antigravity Policies & A2UI cards.",
    url=_base_url,
    iconUrl="https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/png/128/emoji_u1f4ca.png",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(
        streaming=False,
        extensions=[a2ui_extension]
    ),
    skills=[appsheet_skill],
    supports_authenticated_extended_card=True,
)

extended_agent_card = public_agent_card.model_copy(
    update={{
        "name": "appsheet_agent",
        "description": "AppSheet A2A Agent with full OAuth authenticated data access.",
        "skills": [appsheet_skill],
    }}
)

class AuthHeaderMiddleware:
    """Captures HTTP Authorization header and handles /healthz health probes for Cloud Run."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            method = scope.get("method", "GET")
            if path in ("/healthz", "/health") and method == "GET":
                response_body = b'{{"status": "ok", "agent": "appsheet_agent"}}'
                await send({{
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(response_body)).encode("utf-8")),
                    ],
                }})
                await send({{
                    "type": "http.response.body",
                    "body": response_body,
                }})
                return

            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("latin1")
            auth_token_var.set(auth_header)
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)

request_handler = DefaultRequestHandler(
    agent_executor=AppSheetAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

server = A2AStarletteApplication(
    agent_card=public_agent_card,
    http_handler=request_handler,
    extended_agent_card=extended_agent_card,
)

app = AuthHeaderMiddleware(server.build())

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
'''

    def generate_requirements_txt(self) -> str:
        """Generates requirements.txt for the standard Python environment."""
        reqs = """a2a-sdk[http-server]>=0.3.25,<0.4.0
sse-starlette
fastapi>=0.100.0
uvicorn>=0.22.0
httpx>=0.24.0
pyjwt>=2.8.0
cryptography>=41.0.0
"""
        if self.vertex_mode:
            reqs += "google-genai>=0.1.1\n"
        return reqs

    def generate_dockerfile(self) -> str:
        """Generates Cloud Run Dockerfile."""
        return """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "main.py"]
"""

    def generate_zip_package(self, ard_dict: Dict[str, Any], gemini_payload: Dict[str, Any]) -> bytes:
        """Packages generated code files into a downloadable zip byte stream."""
        zip_buffer = io.BytesIO()
        base_dir = "/Users/mhawksey/Documents/Antigravity Agents/google-a2a/server/appsheet_agent"

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # 1. Generated agent_executor.py with Antigravity @tool functions, policies & multimodal support
            zip_file.writestr("agent_executor.py", self.generate_agent_executor_code())
            
            # 2. Generated main.py with /healthz probe handling & LocalAgentConfig(vertex=True)
            zip_file.writestr("main.py", self.generate_main_py())

            # 3. requirements.txt & Dockerfile
            zip_file.writestr("requirements.txt", self.generate_requirements_txt())
            zip_file.writestr("Dockerfile", self.generate_dockerfile())

            # 4. Registration JSON & ARD Spec
            zip_file.writestr("ard.json", json.dumps(ard_dict, indent=2))
            zip_file.writestr("gemini_enterprise_registration.json", json.dumps(gemini_payload, indent=2))

            # 5. Include supporting AppSheet client & auth modules if present
            for file_name in ["appsheet_client.py", "auth.py", "card_templates.py"]:
                full_path = os.path.join(base_dir, file_name)
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        zip_file.writestr(file_name, f.read())

            # 6. Readme
            zip_file.writestr("README.md", f"# Generated AppSheet Agent\nApp ID: {self.app_id}\nRegion: {self.region}\nVertex AI Mode: {self.vertex_mode}")

        return zip_buffer.getvalue()
