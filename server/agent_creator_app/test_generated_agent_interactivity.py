import os
import sys
import json
import jwt
import shutil
import tempfile
import importlib
import asyncio
from unittest.mock import MagicMock, patch

from app.openapi_parser import AppSheetOpenAPIParser
from app.agent_generator import AgentCodeGenerator

# Mock EventQueue to capture enqueued events
class MockEventQueue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)

# Mock RequestContext
class MockRequestContext:
    def __init__(self, message=None, metadata=None, context_id="ctx-123", task_id="task-123"):
        self.message = message
        self.metadata = metadata or {}
        self.context_id = context_id
        self.task_id = task_id
        self.activated_extensions = []

    def add_activated_extension(self, extension):
        self.activated_extensions.append(extension)

from a2a.types import Part, TextPart, DataPart, Message, Role

async def test_generated_agent_interactivity():
    # 1. Locate Planner App openapi.json
    spec_path = "/Users/mhawksey/Documents/Antigravity Agents/Docs/Planner App/openapi.json"
    if not os.path.exists(spec_path):
        print(f"Skipping interactivity test: OpenAPI spec not found at {spec_path}")
        return

    print("Step 1: Parsing AppSheet OpenAPI schema...")
    parser = AppSheetOpenAPIParser.from_file(spec_path)
    tables = parser.get_tables()
    app_id = parser.get_app_id()

    dummy_jwt = jwt.encode({"email": "martin.hawksey@devoteam.com"}, "secret", algorithm="HS256")

    # Define capabilities from example conversation (Users & Tasks find and add)
    capabilities = [
        {"table": "Users", "action": "Find", "description": "List users"},
        {"table": "Tasks", "action": "Find", "description": "List tasks"},
        {"table": "Tasks", "action": "Add", "description": "Create task"},
        {"table": "Tasks", "action": "Edit", "description": "Edit task"}
    ]

    print("Step 1.5: Processing Application Documentation.pdf...")
    doc_path = "/Users/mhawksey/Documents/Antigravity Agents/Docs/Planner App/Application Documentation.pdf"
    doc_context = ""
    if os.path.exists(doc_path):
        with open(doc_path, "rb") as f:
            pdf_bytes = f.read()
        from app.pdf_preprocessor import PDFTokenPreprocessor
        pdf_prep = PDFTokenPreprocessor(pdf_bytes)
        raw_text = pdf_prep.extract_clean_text()
        doc_context = pdf_prep.optimize_for_openapi(raw_text, tables)
        print(f"Extracted PDF doc_context: {len(doc_context)} chars")

    print("Step 2: Generating hybrid agent executor code...")
    generator = AgentCodeGenerator(
        app_id=app_id,
        access_key="dummy-key",
        region="global",
        tables=tables,
        vertex_mode=True,
        gcp_project="a2ui-ge",
        capabilities=capabilities,
        doc_context=doc_context
    )
    executor_code = generator.generate_agent_executor_code()

    # 2. Build temporary package directory to dynamically load the agent
    temp_dir = tempfile.mkdtemp()
    print(f"Step 3: Setting up dynamic execution environment in {temp_dir}...")
    try:
        # Write executor
        with open(os.path.join(temp_dir, "agent_executor.py"), "w", encoding="utf-8") as f:
            f.write(executor_code)

        # Copy supporting modules from server/appsheet_agent
        template_dir = "/Users/mhawksey/Documents/Antigravity Agents/google-a2a/server/appsheet_agent"
        for fn in ["appsheet_client.py", "auth.py", "card_templates.py"]:
            shutil.copy(os.path.join(template_dir, fn), os.path.join(temp_dir, fn))

        # Add temp_dir to system path to import it
        sys.path.insert(0, temp_dir)

        # Mock JWT verification to immediately authorize user email
        import auth
        auth.validate_jwt = MagicMock(return_value={"email": "martin.hawksey@devoteam.com"})

        # Mock AppSheet Client find and add database operations
        import appsheet_client
        mock_client = MagicMock()
        mock_client.find.side_effect = lambda table_name, rows=None: (
            [{"Email": "alice@example.com", "Name": "Alice", "Role": "Admin"}] if "user" in table_name.lower()
            else [{"TaskID": "TASK-1", "TaskName": "API Integration", "Status": "In Progress"}]
        )
        mock_client.add.return_value = {"Rows": [{"TaskID": "TASK-2", "TaskName": "New Test Task"}]}
        appsheet_client.AppSheet = MagicMock(return_value=mock_client)

        # Dynamically import the generated AppSheetAgentExecutor
        import agent_executor
        importlib.reload(agent_executor)
        
        executor = agent_executor.AppSheetAgentExecutor()

        # --- Interactivity Scenario A: Query / List records ---
        print("Interactivity Test Scenario A: Fetch / List users...")
        list_context = MockRequestContext(
            message=Message(
                messageId="msg-1",
                role=Role.user,
                parts=[Part(root=TextPart(text="Retrieve all records from the Users table"))],
                task_id="task-123",
                context_id="ctx-123"
            ),
            metadata={"Authorization": f"Bearer {dummy_jwt}"}
        )
        event_queue = MockEventQueue()

        # Execute query against live Vertex AI endpoint
        await executor.execute(list_context, event_queue)
        
        assert len(event_queue.events) > 0, "No response event received!"
        res_msg = event_queue.events[0]
        
        # Verify A2UI card parts exist, use correct mimeType, and do not use "Table" component
        a2ui_parts = []
        for p in res_msg.parts:
            if isinstance(p.root, DataPart):
                assert p.root.metadata.get("mimeType") == "application/json+a2ui", f"Invalid A2UI mimeType: {p.root.metadata}"
                a2ui_parts.append(p.root.data)
        assert len(a2ui_parts) > 0, "No A2UI card parts generated!"
        
        # Verify A2UI card components filter hidden fields and prioritize label columns
        has_name_label = False
        has_rownumber = False
        for part in a2ui_parts:
            if "surfaceUpdate" in part:
                components = part["surfaceUpdate"]["components"]
                for comp in components:
                    comp_body = comp.get("component", {})
                    # Check list or record card structure
                    assert "Table" not in comp_body, "Invalid 'Table' component found in card!"
                    if "Text" in comp_body:
                        text_val = comp_body["Text"]["text"].get("literalString", "")
                        if "RowNumber" in text_val or "_RowNumber" in text_val:
                            has_rownumber = True
                        # The first field (field_0) in the detail card must be the Label column (Name: Alice)
                        if comp.get("id") == "field_0" and "• Name: Alice" in text_val:
                            has_name_label = True

        assert not has_rownumber, "Hidden system column _RowNumber was leaked and rendered in card!"
        assert has_name_label, "Primary label column 'Name' was not prioritized and rendered as field_0!"
        print("✅ Interactivity Scenario A Passed! List/Record views rendered without hidden fields and prioritized label columns.")

        # --- Interactivity Scenario B: Write command interception to render Form Card ---
        print("Interactivity Test Scenario B: Form interception...")
        add_context = MockRequestContext(
            message=Message(
                messageId="msg-2",
                role=Role.user,
                parts=[Part(root=TextPart(text="add task"))],
                task_id="task-123",
                context_id="ctx-123"
            ),
            metadata={"Authorization": f"Bearer {dummy_jwt}"}
        )
        event_queue = MockEventQueue()
        
        # Execute interception
        await executor.execute(add_context, event_queue)
        
        assert len(event_queue.events) > 0, "No response event received!"
        res_msg = event_queue.events[0]
        
        # Verify A2UI form card parts exist and use correct mimeType
        a2ui_parts = []
        for p in res_msg.parts:
            if isinstance(p.root, DataPart):
                assert p.root.metadata.get("mimeType") == "application/json+a2ui", f"Invalid A2UI mimeType: {p.root.metadata}"
                a2ui_parts.append(p.root.data)
        assert len(a2ui_parts) > 0, "No A2UI card parts generated for form command!"
        
        # Verify form fields are rendered
        has_form_fields = False
        for part in a2ui_parts:
            if "surfaceUpdate" in part:
                components = part["surfaceUpdate"]["components"]
                for comp in components:
                    comp_body = comp.get("component", {})
                    if "TextField" in comp_body or "CheckBox" in comp_body or "DateTimeInput" in comp_body:
                        has_form_fields = True
                        
        assert has_form_fields, "Form layout card lacks input fields!"
        print("✅ Interactivity Scenario B Passed! Add task prompt intercepted to render A2UI form card.")

        # --- Interactivity Scenario C: Submit Form Event ---
        print("Interactivity Test Scenario C: Submit Form Event...")
        submit_context = MockRequestContext(
            message=Message(
                messageId="msg-3",
                role=Role.user,
                parts=[Part(root=DataPart(data={
                    "userAction": {
                        "name": "submit_add_tasks",
                        "context": [
                            {"key": "TaskName", "value": "Write Interactivity Unit Tests"},
                            {"key": "Description", "value": "Verification checks"},
                            {"key": "DueDate", "value": "2026-07-20"}
                        ]
                    }
                }))],
                task_id="task-123",
                context_id="ctx-123"
            ),
            metadata={"Authorization": f"Bearer {dummy_jwt}"}
        )
        event_queue = MockEventQueue()
        
        # Execute submit
        await executor.execute(submit_context, event_queue)
        
        # Check if mocked AppSheet add was called
        assert mock_client.add.called, "Database add client method was not invoked on submit!"
        called_args = mock_client.add.call_args[1]
        assert called_args["table_name"] == "Tasks", "Incorrect table targeted on database add!"
        
        # Verify return payload contains success confirmation card with correct mimeType
        assert len(event_queue.events) > 0, "No submit response event received!"
        res_msg = event_queue.events[0]
        
        a2ui_parts = []
        for p in res_msg.parts:
            if isinstance(p.root, DataPart):
                assert p.root.metadata.get("mimeType") == "application/json+a2ui", f"Invalid A2UI mimeType: {p.root.metadata}"
                a2ui_parts.append(p.root.data)
        
        has_success_card = False
        for part in a2ui_parts:
            if "surfaceUpdate" in part:
                components = part["surfaceUpdate"]["components"]
                for comp in components:
                    comp_body = comp.get("component", {})
                    if "Text" in comp_body:
                        lit = comp_body["Text"]["text"].get("literalString", "")
                        if "Successfully" in lit or "Success" in lit:
                            has_success_card = True
                            
        assert has_success_card, "Submit response lacks success confirmation card!"
        # --- Interactivity Scenario D: Submit Edit Form Event ---
        print("Interactivity Test Scenario D: Submit Edit Form Event...")
        mock_client.edit.reset_mock()
        mock_client.edit.return_value = {"Rows": [{"TaskID": "TASK-1", "Status": "Completed"}]}
        
        edit_context = MockRequestContext(
            message=Message(
                messageId="msg-4",
                role=Role.user,
                parts=[Part(root=DataPart(data={
                    "userAction": {
                        "name": "submit_edit_tasks",
                        "context": [
                            {"key": "TaskID", "value": "TASK-1"},
                            {"key": "Status", "value": "Completed"},
                            {"key": "Description", "value": ""} # Should be filtered out by format/non_empty
                        ]
                    }
                }))],
                task_id="task-123",
                context_id="ctx-123"
            ),
            metadata={"Authorization": f"Bearer {dummy_jwt}"}
        )
        event_queue = MockEventQueue()
        
        # Execute edit submit
        await executor.execute(edit_context, event_queue)
        
        # Check if mocked AppSheet edit was called
        assert mock_client.edit.called, "Database edit client method was not invoked on submit!"
        called_args = mock_client.edit.call_args[1]
        assert called_args["table_name"] == "Tasks", "Incorrect table targeted on database edit!"
        # Verify empty description was filtered out, and TaskID and Status were sent
        assert called_args["rows"] == [{"TaskID": "TASK-1", "Status": "Completed"}], f"Unexpected edit rows payload: {called_args['rows']}"
        print("✅ Interactivity Scenario D Passed! Edit form submit event executed database write and updated records.")

    finally:
        # Clean up system path and temp files
        if temp_dir in sys.path:
            sys.path.remove(temp_dir)
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(test_generated_agent_interactivity())
    print("🎉 All Generated Agent Interactivity Integration tests passed!")
