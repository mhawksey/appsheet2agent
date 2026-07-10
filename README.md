# Google A2A: AppSheet Agent Creator Studio & Antigravity SDK Architecture

> **Attribution:** This repository is an adaptation and extension of the [alphasecio/google-a2a](https://github.com/alphasecio/google-a2a) repository, originally referenced in the blog post: [From A2A Agent to Gemini Enterprise: A Practical Deployment Guide](https://alphasec.io/from-a2a-agent-to-gemini-enterprise-a-practical-deployment-guide/). It has been significantly expanded into a full-featured **AppSheet Agent Creator Studio & ARD Generator** powered by the **Google Antigravity SDK (`google.antigravity`)**, **A2A Protocol**, **OAuth 2.0 User Email Delegation**, and **A2UI v0.8 Visual Cards**.

---

## ⚡ Overview

**AppSheet Agent Creator Studio** empowers developers and business architects to transform any AppSheet database or application specification into a production-ready, autonomous AI Agent for **Gemini Enterprise**.

The Studio automates the full lifecycle — from parsing `openapi.json` specs and PDF documentation to interactive Specialist Agent consulting, ARD manifest generation, security policy enforcement, and 1-click Google Cloud Run deployment.

---

## 🔥 Key Architectural Features

### 1. 🤖 Google Antigravity SDK Integration (`google.antigravity`)
- **Native `@tool` Decorators**: Generates strongly-typed `@tool` Python functions for all AppSheet tables and CRUD actions.
- **Declarative Security Policies (`hooks.policy`)**: Enforces zero-trust tool access rules (`deny("*")`, `allow("find_*")`, `ask_user("add_*")`).
- **Multimodal Attachment Ingestion (`types.from_file` & `types.Image`)**: Automatically detects image/photo columns (e.g. `Headshot`, `Floorplan`, `Photo`) and ingests media assets into agent prompts.
- **GCP Vertex AI Mode (`LocalAgentConfig(vertex=True)`)**: Toggleable support for native GCP Vertex AI authentication and project configuration.

### 2. 🔐 OAuth User Delegation (`RunAsUserEmail`)
- Enforces user identity delegation by capturing Google OAuth JWT claims (`email`).
- All AppSheet API operations execute strictly under the authentic user's identity via `RunAsUserEmail: 'user@domain.com'`.

### 3. 🎨 A2UI v0.8 Visual Card Component Engine
- Generates interactive A2UI v0.8 cards (`standard_catalog_definition.json`) inside Gemini Enterprise chat turns.
- Renders rich visual record cards for table search results, status updates, and form submissions.

### 4. 📁 AppSheet Management App Integration
- Connects directly to the AppSheet Management App (`c61d70ac-1a98-4c36-b735-593f6eeb60b3`).
- Saves, updates, and reloads creator agent sessions directly from AppSheet tables.

### 5. 🚀 Instant Browser Download & Customized Deployment Script
- Automatically packages and downloads the generated agent as a `.zip` package (`appsheet_agent_package_<app_id>.zip`).
- Pre-populates customized, copy-pasteable Google Cloud Run terminal deployment scripts (`gcloud run deploy`).

### 6. 💫 Glassmorphic Progress Loading Overlay
- Real-time progress overlay window with an animated spinner and dynamic status messages during async operations.

---

## 📁 Repository Structure

```
google-a2a/
├── server/
│   ├── agent_creator_app/     # ⚡ AppSheet Agent Creator Studio Web Application
│   │   ├── app/
│   │   │   ├── main.py                # FastAPI endpoints (/api/upload_and_parse, /api/generate_agent, etc.)
│   │   │   ├── specialist_agent.py    # Specialist Agent Architect consulting engine & 2-Phase plans
│   │   │   ├── agent_generator.py     # Code generator (Antigravity SDK tools, policies, zip packaging)
│   │   │   ├── ard_generator.py       # ARD Spec v1.0 & Gemini Enterprise Registration JSON builder
│   │   │   ├── openapi_parser.py      # AppSheet openapi.json parser
│   │   │   ├── management_client.py   # AppSheet Management App API client
│   │   │   └── pdf_preprocessor.py    # PDF documentation preprocessor
│   │   └── static/
│   │       ├── index.html             # Studio Web UI layout
│   │       ├── styles.css             # Dark mode theme & glassmorphic progress overlay modal
│   │       ├── app.js                 # Studio frontend logic & GIS OAuth handlers
│   │       └── a2ui_renderer.js       # Client-side A2UI v0.8 card renderer
│   │
│   ├── appsheet_agent/        # 🤖 Runnable Hybrid A2A + Antigravity SDK Agent template
│   │   ├── main.py                # Cloud Run Starlette app with /healthz probe
│   │   ├── agent_executor.py      # AgentExecutor with @tool functions & A2UI cards
│   │   ├── appsheet_client.py     # AppSheet REST API client with RunAsUserEmail
│   │   ├── auth.py                # OAuth JWT validator & ContextVar token store
│   │   └── card_templates.py      # A2UI card generators
│   │
│   ├── hello_oauth/           # Reference OAuth 2.0 A2A Server
│   └── hello_apikey/          # Reference API-key A2A Server
└── client/                    # Test CLI & Streamlit Clients
```

---

## 🚀 Quick Start Guide

### 1. Launch AppSheet Agent Creator Studio Locally

```bash
cd server/agent_creator_app

# Install dependencies
pip install -r requirements.txt

# Run the Creator Studio server
uvicorn app.main:app --port 8000 --reload
```

Open **`http://localhost:8000`** in your browser.

---

### 2. Design & Generate Your Agent

1. **Sign in with Google OAuth** or enter your user email in the top navbar.
2. Select a saved agent from your **Management App** or upload `openapi.json` + PDF documentation.
3. Consult with the **Specialist Agent Architect** in the interactive chat sandbox to refine table capabilities.
4. Option: Check **Enable GCP Vertex AI Mode (`LocalAgentConfig(vertex=True)`)** if deploying to Vertex AI.
5. Click **Generate Agent & ARD Spec**:
   - Browser automatically downloads `appsheet_agent_package_<app_id>.zip`.
   - Customized **Cloud Run Deployment Script** and **Gemini Enterprise Admin Registration JSON** appear in Section 4!

---

### 3. Deploy Generated Agent to Google Cloud Run

Unzip your downloaded agent package:
```bash
unzip appsheet_agent_package_40c823df-3005-4dea-9d32-2197837ce3e7.zip -d appsheet-agent
cd appsheet-agent
```

Deploy to Google Cloud Run:
```bash
gcloud run deploy facility-inspections-agent \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars APPSHEET_APP_ID="40c823df-3005-4dea-9d32-2197837ce3e7",APPSHEET_ACCESS_KEY="V2-xxxx-xxxx",APPSHEET_REGION="www.appsheet.com"
```

---

### 4. Register in Gemini Enterprise

1. Open **Gemini Enterprise Admin Console** -> **Agents** -> **Add Custom Agent**.
2. Paste the **Gemini Enterprise Admin Registration JSON** generated by Section 4 of the Studio.
3. Copy your Cloud Run URL into the `endpointUrl` field.
4. Your AppSheet AI Agent is live and ready for corporate users!

---

## 🛠️ Technology Stack

- **Framework**: Python 3.11, FastAPI, Starlette, Uvicorn
- **Agent Architecture**: Google Antigravity SDK (`google.antigravity`), A2A Protocol, A2UI v0.8
- **Authentication**: OAuth 2.0 (Google Identity Services GIS), JWT, `RunAsUserEmail` delegation
- **Database Target**: AppSheet REST API (v2)
- **Deployment**: Google Cloud Run, Docker
