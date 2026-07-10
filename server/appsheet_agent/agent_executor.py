"""
AppSheet A2A Agent Executor Template.

This class manages incoming user prompts, enforces OAuth validation, retrieves the
authenticated user's email address, initializes the AppSheet client with RunAsUserEmail,
and returns formatted A2UI v0.8 cards.

AI ASSISTANT GUIDE - ADAPTING THIS BOILERPLATE FOR YOUR APPSHEET APP:
--------------------------------------------------------------------
1. Define your AppSheet Table Name:
   Change `DEFAULT_TABLE_NAME` below to match your AppSheet app's target table (e.g., "Tasks", "Inventory").

2. Customize Table Operations:
   In `execute()`, look at the `find`, `add`, `edit`, and `delete` handlers.
   Update row dictionaries (e.g., {"TaskName": "...", "Status": "Open"}) to match your table columns.

3. Customize Response Cards:
   Use `card_templates.create_record_card()` or `card_templates.create_status_card()` to format output.
"""

import os
from typing import List, Dict, Any, Optional

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Part, TextPart, DataPart, Message, Role, 
    TaskStatusUpdateEvent, TaskStatus, TaskState
)
from a2a.utils import new_agent_text_message, new_agent_parts_message
from datetime import datetime, timezone

from appsheet_client import AppSheet
from auth import auth_token_var, validate_jwt
from card_templates import create_record_card, create_status_card

# ==============================================================================
# PLACEHOLDER CONFIGURATION - CUSTOMIZE THIS FOR YOUR APPSHEET APP
# ==============================================================================
DEFAULT_TABLE_NAME = os.environ.get("APPSHEET_DEFAULT_TABLE", "Tasks")

class AppSheetAgentExecutor(AgentExecutor):
    """
    Boilerplate AgentExecutor connecting Gemini Enterprise to AppSheet apps.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Activate A2UI extension catalog
        context.add_activated_extension("https://a2ui.org/a2a-extension/a2ui/v0.8")

        # 1. Extract User Message Text
        user_text = ""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, "root") and hasattr(part.root, "text"):
                    user_text = part.root.text.strip()
                    break

        # 2. Extract & Validate OAuth Bearer Token
        token = auth_token_var.get().removeprefix("Bearer ").strip()
        
        # Fallback search in context metadata if header middleware wasn't triggered
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

        # 3. Handle Missing OAuth Token -> Return auth_required state
        if not token:
            print("[AppSheetAgent] Missing OAuth token. Requesting authentication.", flush=True)
            auth_event = TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=False,
                status=TaskStatus(
                    state=TaskState.auth_required,
                    message=Message(
                        role=Role.agent,
                        parts=[Part(root=TextPart(text="Authentication required to access your AppSheet data."))],
                        task_id=context.task_id or "",
                        context_id=context.context_id or "",
                    ),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            await event_queue.enqueue_event(auth_event)
            return

        # 4. Validate Token & Extract User Email
        try:
            claims = validate_jwt(token)
            user_email = (
                claims.get("email") 
                or claims.get("upn") 
                or claims.get("preferred_username") 
                or ""
            )
            print(f"[AppSheetAgent] Authenticated user email: '{user_email}'", flush=True)
        except Exception as e:
            print(f"[AppSheetAgent] Token validation failed: {e}", flush=True)
            await event_queue.enqueue_event(
                new_agent_text_message("❌ Authentication failed: Invalid or expired OAuth token.")
            )
            return

        if not user_email:
            await event_queue.enqueue_event(
                new_agent_text_message("❌ Unable to determine user email address from OAuth token.")
            )
            return

        # 5. Instantiate AppSheet API Client with User Email (Enforces RunAsUserEmail)
        try:
            client = AppSheet(user_email=user_email)
        except ValueError as e:
            await event_queue.enqueue_event(
                new_agent_text_message(f"⚠️ AppSheet configuration error: {e}")
            )
            return

        # ==============================================================================
        # AI ASSISTANT / DEVELOPER ROUTING LOGIC - ADAPT COMMANDS FOR YOUR APP
        # ==============================================================================
        cmd = user_text.lower()

        # ------------------------------------------------------------------------------
        # ACTION: FIND / SEARCH RECORDS
        # ------------------------------------------------------------------------------
        if "find" in cmd or "get" in cmd or "list" in cmd or "show" in cmd:
            print(f"[AppSheetAgent] Executing Find on table '{DEFAULT_TABLE_NAME}' for {user_email}", flush=True)
            
            # Call AppSheet API (RunAsUserEmail is automatically injected!)
            result = client.find(table_name=DEFAULT_TABLE_NAME)

            if "error" in result:
                await event_queue.enqueue_event(
                    new_agent_text_message(f"❌ Error querying AppSheet table '{DEFAULT_TABLE_NAME}': {result['error']}")
                )
                return

            records = result if isinstance(result, list) else result.get("Rows", [])
            
            if not records:
                await event_queue.enqueue_event(
                    new_agent_text_message(f"📋 No records found in AppSheet table '{DEFAULT_TABLE_NAME}'.")
                )
                return

            # Display first record in an A2UI v0.8 card
            first_record = records[0]
            card_commands = create_record_card(
                surface_id="appsheet-record-card",
                title=f"AppSheet: {DEFAULT_TABLE_NAME} Record",
                record_data=first_record
            )

            msg = new_agent_parts_message(
                parts=[
                    Part(root=TextPart(text=f"Fetched {len(records)} record(s) from table '{DEFAULT_TABLE_NAME}' as {user_email}:")),
                    *[
                        Part(root=DataPart(
                            data=c,
                            metadata={"mimeType": "application/json+a2ui"}
                        ))
                        for c in card_commands
                    ]
                ],
                context_id=context.context_id,
                task_id=context.task_id,
            )
            await event_queue.enqueue_event(msg)
            return

        # ------------------------------------------------------------------------------
        # ACTION: ADD RECORD (PLACEHOLDER TEMPLATE)
        # ------------------------------------------------------------------------------
        elif "add" in cmd or "create" in cmd:
            # AI ASSISTANT NOTE: Modify row dictionary to match your AppSheet table columns
            sample_row = {
                "Title": "New Item from Agent",
                "Description": f"Created via A2A Agent by {user_email}",
                "Status": "Open"
            }
            print(f"[AppSheetAgent] Executing Add on table '{DEFAULT_TABLE_NAME}' for {user_email}", flush=True)
            result = client.add(table_name=DEFAULT_TABLE_NAME, rows=[sample_row])

            success = "error" not in result
            status_card = create_status_card(
                surface_id="add-status-card",
                title="Add Record Result",
                message=f"Created record in '{DEFAULT_TABLE_NAME}' on behalf of {user_email}." if success else f"Error: {result.get('error')}",
                success=success
            )

            msg = new_agent_parts_message(
                parts=[
                    Part(root=TextPart(text=f"Add Record Operation Status:")),
                    *[
                        Part(root=DataPart(
                            data=c,
                            metadata={"mimeType": "application/json+a2ui"}
                        ))
                        for c in status_card
                    ]
                ],
                context_id=context.context_id,
                task_id=context.task_id,
            )
            await event_queue.enqueue_event(msg)
            return

        # ------------------------------------------------------------------------------
        # DEFAULT / HELP RESPONSE
        # ------------------------------------------------------------------------------
        help_text = (
            f"👋 AppSheet Agent Ready!\n\n"
            f"Authenticated as: **{user_email}**\n"
            f"App ID: `{client.app_id}`\n"
            f"Region: `{client.appsheet_region}`\n"
            f"Default Table: `{DEFAULT_TABLE_NAME}`\n\n"
            f"Try commands like:\n"
            f"• *'show records'* - Queries table '{DEFAULT_TABLE_NAME}'\n"
            f"• *'add record'* - Demonstrates creating a record with RunAsUserEmail\n"
        )
        await event_queue.enqueue_event(new_agent_text_message(help_text))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel operation not supported.")
