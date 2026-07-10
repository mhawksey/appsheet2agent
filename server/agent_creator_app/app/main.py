"""
FastAPI Server for AppSheet Agent Creator Web Application.
Exposes UI endpoints, schema parsers, code scaffolder, live test chat sandbox,
and Management App (AppSheet2Agent) integration.
"""

import base64
import json
import os
import sys
import zlib

def compress_string(text: str) -> str:
    """Compresses long string content using zlib & base64 to fit in database cells."""
    if not text:
        return ""
    compressed_bytes = zlib.compress(text.encode('utf-8'), level=9)
    b64_str = base64.b64encode(compressed_bytes).decode('utf-8')
    return f"compressed://{b64_str}"

def decompress_string(text: str) -> str:
    """Decompresses string content if it starts with the compressed prefix."""
    if text.startswith("compressed://"):
        try:
            b64_str = text.split("compressed://")[1]
            compressed_bytes = base64.b64decode(b64_str)
            return zlib.decompress(compressed_bytes).decode('utf-8')
        except Exception as e:
            print(f"[Decompress] Error decompressing string: {e}")
            return text
    return text
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# Add appsheet_agent to path to import AppSheet client
sys.path.append(os.path.join(os.path.dirname(__file__), "../../appsheet_agent"))
from appsheet_client import AppSheet

from fastapi import FastAPI, UploadFile, File, Form, Response, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List, Dict, Any

from app.openapi_parser import AppSheetOpenAPIParser
from app.pdf_preprocessor import PDFTokenPreprocessor
from app.ard_generator import ARDGenerator
from app.agent_generator import AgentCodeGenerator
from app.management_client import ManagementAppClient
from app.specialist_agent import SpecialistAgentArchitect

app = FastAPI(title="AppSheet Agent Creator Web App")

# In-memory storage for active wizard session
session_store: Dict[str, Any] = {
    "parsed_tables": {},
    "app_id": "",
    "app_title": "",
    "doc_context": "",
    "raw_openapi_json": "",
    "active_capabilities": [],
    "sample_data": {}
}

DEFAULT_DOCS_PATH = "/Users/mhawksey/Documents/Antigravity Agents/Docs/openapi.json"

def decode_appsheet_file_content(content_str: str) -> str:
    """Decodes Base64 Data URI strings or returns raw text."""
    if not content_str:
        return ""
    if content_str.startswith("data:") and ";base64," in content_str:
        try:
            b64_data = content_str.split(";base64,")[1]
            return base64.b64decode(b64_data).decode("utf-8")
        except Exception:
            return content_str
    return content_str


@app.post("/api/upload_and_parse")
async def upload_and_parse(
    openapi_file: UploadFile = File(...),
    doc_file: Optional[UploadFile] = File(None)
):
    try:
        openapi_content = (await openapi_file.read()).decode("utf-8")
        parser = AppSheetOpenAPIParser.from_string(openapi_content)
        tables = parser.get_tables()
        app_id = parser.get_app_id()
        app_title = parser.get_app_title()

        doc_context = ""
        if doc_file:
            pdf_bytes = await doc_file.read()
            pdf_prep = PDFTokenPreprocessor(pdf_bytes)
            raw_text = pdf_prep.extract_clean_text()
            doc_context = pdf_prep.optimize_for_openapi(raw_text, tables)

        session_store["parsed_tables"] = tables
        session_store["app_id"] = app_id
        session_store["app_title"] = app_title
        session_store["doc_context"] = doc_context
        session_store["raw_openapi_json"] = openapi_content
        session_store["active_capabilities"] = []
        session_store["conversation_id"] = None

        specialist = SpecialistAgentArchitect(parsed_tables=tables, doc_context=doc_context)
        greeting_data = specialist.generate_greeting(app_title=app_title)

        return {
            "status": "success",
            "app_title": app_title,
            "app_id": app_id,
            "tables_found": list(tables.keys()),
            "table_details": tables,
            "doc_context_length": len(doc_context),
            "specialist_greeting": greeting_data["response_text"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse files: {str(e)}")


@app.get("/api/management/agents")
async def list_management_agents(user_email: str = "creator_test@company.com"):
    try:
        mgmt_client = ManagementAppClient(user_email=user_email)
        agents = mgmt_client.list_user_agents()
        return {"status": "success", "agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying Management App: {str(e)}")


@app.post("/api/management/load_agent_session")
async def load_agent_session(
    app_id: str = Form(...),
    user_email: str = Form("creator_test@company.com")
):
    try:
        mgmt_client = ManagementAppClient(user_email=user_email)
        agents = mgmt_client.list_user_agents()

        target_agent = None
        for a in agents:
            if a.get("app_id") == app_id:
                target_agent = a
                break

        if not target_agent:
            raise HTTPException(status_code=404, detail=f"Agent '{app_id}' not found in Management App.")

        openapi_raw = target_agent.get("openapi_json", "")
        doc_raw = target_agent.get("processed_app_definition", "")

        from app.gcs_client import GCSClient
        gcs_client = None

        if openapi_raw.startswith("gs://"):
            try:
                gcs_client = GCSClient()
                openapi_raw = gcs_client.download_text(openapi_raw)
            except Exception as e:
                print(f"[GCS] Error downloading openapi from GCS ({openapi_raw}): {e}")
                openapi_raw = ""

        if doc_raw.startswith("gs://"):
            try:
                if gcs_client is None:
                    gcs_client = GCSClient()
                doc_raw = gcs_client.download_text(doc_raw)
            except Exception as e:
                print(f"[GCS] Error downloading doc_context from GCS ({doc_raw}): {e}")
        openapi_raw = decompress_string(openapi_raw)
        doc_raw = decompress_string(doc_raw)

        tables = {}
        app_title = f"AppSheet App ({app_id})"

        # Fallback to local Docs/openapi.json if openapi_raw is a Google Drive path or empty
        if not openapi_raw or not openapi_raw.strip().startswith("{"):
            if os.path.exists(DEFAULT_DOCS_PATH):
                with open(DEFAULT_DOCS_PATH, "r", encoding="utf-8") as f:
                    openapi_raw = f.read()

        if openapi_raw and openapi_raw.strip().startswith("{"):
            try:
                parser = AppSheetOpenAPIParser.from_string(openapi_raw)
                tables = parser.get_tables()
                app_title = parser.get_app_title()
            except Exception:
                pass

        session_store["parsed_tables"] = tables
        session_store["app_id"] = app_id
        session_store["app_title"] = app_title
        session_store["doc_context"] = doc_raw
        session_store["raw_openapi_json"] = openapi_raw
        session_store["active_capabilities"] = []
        session_store["conversation_id"] = None

        specialist = SpecialistAgentArchitect(parsed_tables=tables, doc_context=doc_raw)
        greeting_data = specialist.generate_greeting(app_title=app_title)

        return {
            "status": "success",
            "app_id": app_id,
            "app_title": app_title,
            "tables_found": list(tables.keys()),
            "table_details": tables,
            "doc_context": doc_raw,
            "specialist_greeting": greeting_data["response_text"],
            "appsheet_key": target_agent.get("appsheet_key", ""),
            "deployed_url": target_agent.get("deployed_url", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load agent session: {str(e)}")


@app.post("/api/management/save_agent")
async def save_management_agent(
    app_id: str = Form(...),
    appsheet_key: str = Form(...),
    user_email: str = Form("creator_test@company.com"),
    status: str = Form("Draft"),
    deployed_url: str = Form("")
):
    try:
        mgmt_client = ManagementAppClient(user_email=user_email)
        openapi_content = session_store.get("raw_openapi_json", "{}")
        doc_content = session_store.get("doc_context", "")

        openapi_val = openapi_content
        doc_val = doc_content
        try:
            from app.gcs_client import GCSClient
            gcs_client = GCSClient()
            
            # Save openapi.json to GCS
            openapi_val = gcs_client.upload_text(f"agents/{app_id}/openapi.json", openapi_content)
            
            # Save doc_context to GCS if present
            if doc_content.strip():
                doc_val = gcs_client.upload_text(f"agents/{app_id}/doc_context.txt", doc_content)
            
            print(f"[GCS] Successfully uploaded files for {app_id} to GCS: openapi={openapi_val}, doc={doc_val}")
        except Exception as e:
            print(f"[GCS] Warning: Failed to upload files to GCS ({e}). Compressing and saving raw content directly to AppSheet.")
            openapi_val = compress_string(openapi_content)
            if doc_content.strip():
                doc_val = compress_string(doc_content)

        res = mgmt_client.save_agent(
            app_id=app_id,
            appsheet_key=appsheet_key,
            openapi_json_content=openapi_val,
            processed_doc_content=doc_val,
            status=status,
            deployed_url=deployed_url
        )
        return {"status": "success", "management_response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save agent to Management App: {str(e)}")


@app.post("/api/generate_agent")
async def generate_agent(
    app_id: str = Form(...),
    access_key: str = Form(...),
    region: str = Form("www.appsheet.com"),
    user_email: str = Form("creator_test@company.com"),
    service_url: str = Form("https://appsheet-agent-xyz.a.run.app"),
    client_tables_json: Optional[str] = Form(None),
    client_capabilities_json: Optional[str] = Form(None),
    vertex_mode: Optional[str] = Form("false"),
    gcp_project: Optional[str] = Form("")
):
    tables = session_store.get("parsed_tables", {})

    if not tables and client_tables_json:
        try:
            parsed_client_tables = json.loads(client_tables_json)
            if parsed_client_tables:
                tables = parsed_client_tables
                session_store["parsed_tables"] = tables
        except Exception:
            pass

    if not tables:
        try:
            mgmt_client = ManagementAppClient(user_email=user_email)
            agents = mgmt_client.list_user_agents()
            for a in agents:
                if a.get("app_id") == app_id:
                    openapi_raw = decode_appsheet_file_content(a.get("openapi_json", ""))
                    if not openapi_raw or not openapi_raw.strip().startswith("{"):
                        if os.path.exists(DEFAULT_DOCS_PATH):
                            with open(DEFAULT_DOCS_PATH, "r", encoding="utf-8") as f:
                                openapi_raw = f.read()
                    if openapi_raw and openapi_raw.strip().startswith("{"):
                        parser = AppSheetOpenAPIParser.from_string(openapi_raw)
                        tables = parser.get_tables()
                        session_store["parsed_tables"] = tables
                        session_store["raw_openapi_json"] = openapi_raw
                        session_store["app_title"] = parser.get_app_title()
                    break
        except Exception:
            pass

    if not tables:
        raise HTTPException(
            status_code=400, 
            detail="No parsed tables found. Please upload openapi.json or select a saved agent from the Management App first."
        )

    doc_context = session_store.get("doc_context", "")
    is_vertex_mode = vertex_mode.lower() in ("true", "1", "yes")

    capabilities = []
    if client_capabilities_json:
        try:
            parsed_caps = json.loads(client_capabilities_json)
            if parsed_caps:
                capabilities = parsed_caps
        except Exception:
            pass

    ard_gen = ARDGenerator(
        agent_id=f"appsheet-{app_id[:8]}",
        display_name=session_store.get("app_title", "AppSheet Agent"),
        description="Agent generated via AppSheet Agent Creator Web App",
        appsheet_app_id=app_id,
        service_url=service_url,
        tables=tables,
        capabilities=capabilities
    )

    ard_spec = ard_gen.generate_ard_spec()
    gemini_payload = ard_gen.generate_gemini_enterprise_admin_payload()

    code_gen = AgentCodeGenerator(
        app_id=app_id,
        access_key=access_key,
        region=region,
        tables=tables,
        doc_context=doc_context,
        vertex_mode=is_vertex_mode,
        gcp_project=gcp_project,
        capabilities=capabilities
    )

    zip_bytes = code_gen.generate_zip_package(ard_spec, gemini_payload)

    return {
        "status": "success",
        "ard_spec": ard_spec,
        "gemini_registration_json": gemini_payload,
        "zip_base64": zip_bytes.hex()
    }


@app.post("/api/test_chat")
@app.post("/api/specialist_chat")
async def specialist_chat(
    message: str = Form(...),
    user_email: str = Form("creator_test@company.com"),
    app_id: str = Form(...),
    access_key: str = Form(...),
    region: str = Form("www.appsheet.com"),
    client_tables_json: Optional[str] = Form(None),
    client_capabilities_json: Optional[str] = Form(None)
):
    tables = session_store.get("parsed_tables", {})
    capabilities = session_store.get("active_capabilities", [])

    if client_tables_json:
        try:
            parsed_client_tables = json.loads(client_tables_json)
            if parsed_client_tables:
                tables = parsed_client_tables
                session_store["parsed_tables"] = tables
        except Exception:
            pass

    if client_capabilities_json:
        try:
            parsed_caps = json.loads(client_capabilities_json)
            if parsed_caps:
                capabilities = parsed_caps
        except Exception:
            pass

    doc_context = session_store.get("doc_context", "")

    # Lazily fetch sample data for all tables on first chat
    sample_data = session_store.get("sample_data", {})
    if not sample_data and tables and app_id and access_key:
        try:
            client = AppSheet(app_id=app_id, access_key=access_key, appsheet_region=region, user_email=user_email)
            fetch_requests = []
            table_names = list(tables.keys())
            for t_name in table_names:
                fetch_requests.append(client.find(table_name=t_name, rows=[], defer_execution=True))
            
            # Fetch up to 10 rows per table in parallel
            results = AppSheet.fetch_all(fetch_requests, max_workers=5)
            for i, result in enumerate(results):
                t_name = table_names[i]
                if isinstance(result, list):
                    sample_data[t_name] = result[:10]
                elif isinstance(result, dict) and result.get("Rows"):
                    sample_data[t_name] = result.get("Rows")[:10]
                else:
                    sample_data[t_name] = []
            session_store["sample_data"] = sample_data
        except Exception as e:
            print(f"Failed to fetch sample data: {e}")

    specialist = SpecialistAgentArchitect(parsed_tables=tables, doc_context=doc_context, sample_data=sample_data, region=region)
    result = await specialist.process_creator_dialogue(
        creator_prompt=message,
        user_email=user_email,
        app_id=app_id,
        active_capabilities=capabilities,
        conversation_id=session_store.get("conversation_id")
    )

    if result.get("conversation_id"):
        session_store["conversation_id"] = result.get("conversation_id")

    session_store["active_capabilities"] = result.get("capabilities", [])

    return result

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()
