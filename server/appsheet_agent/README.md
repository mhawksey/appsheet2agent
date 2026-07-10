# AppSheet A2A Boilerplate Agent with OAuth & A2UI v0.8

This directory contains a reusable **AppSheet A2A Agent Boilerplate**. It allows team members and AI coding assistants to quickly build conversational agents for any AppSheet application deployed on Cloud Run and integrated into Gemini Enterprise.

---

## Key Features

1. **Automatic OAuth User Delegation (`RunAsUserEmail`)**:
   Every request made to the AppSheet API (`Find`, `Add`, `Edit`, `Delete`, `Action`) automatically extracts the logged-in user's email address from their OAuth token (`ya29.` Google token or standard OIDC JWT) and injects `"RunAsUserEmail": user_email` into the API payload properties.

2. **Configurable Region Support**:
   Supports standard (`www.appsheet.com`) and data-residency endpoints (e.g. `eu.appsheet.com` or `asia-southeast.appsheet.com`) via the `APPSHEET_REGION` environment variable.

3. **Gemini Enterprise A2UI v0.8 Visual Cards**:
   Includes pre-configured helpers in `card_templates.py` for rendering records and action feedback using the A2UI v0.8 specification required by Gemini Enterprise.

4. **AI Assistant Ready**:
   All core files (`appsheet_client.py`, `agent_executor.py`, `card_templates.py`) include inline guides and placeholders specifically structured for AI coding assistants to adapt the code for new AppSheet tables.

---

## Directory Structure

```
server/appsheet_agent/
├── .env.example              # Template for environment variables
├── Dockerfile                # Cloud Run deployment Dockerfile
├── README.md                 # Developer & AI Assistant Guide
├── __main__.py               # App entrypoint & Starlette header middleware
├── agent_executor.py        # Core agent logic & user message routing
├── appsheet_client.py       # Region-aware AppSheet client with auto RunAsUserEmail
├── auth.py                   # Google OAuth & OIDC token validator
├── card_templates.py        # Modular A2UI v0.8 card generators
└── requirements.txt         # Python dependencies
```

---

## Quick Start Guide

### 1. Configuration (`.env`)
Copy `.env.example` to `.env` and fill in your AppSheet App credentials:

```bash
cp .env.example .env
```

```ini
APPSHEET_APP_ID=your-app-id-here
APPSHEET_ACCESS_KEY=V2-xxxx-xxxx-xxxx
APPSHEET_REGION=www.appsheet.com
APPSHEET_DEFAULT_TABLE=Tasks
```

### 2. Local Testing
Install dependencies and launch the dev server:

```bash
pip install -r requirements.txt
python __main__.py
```

---

## Guide for AI Coding Assistants & Developers

When adapting this boilerplate for a new AppSheet app:

### 1. Changing Table Name & Columns
Open `agent_executor.py`:
- Update `DEFAULT_TABLE_NAME` (or pass custom table names to `client.find("MyTable")`).
- In the `add` or `edit` command branches, modify the dictionary payload to match your table's columns:
  ```python
  new_row = {
      "ColumnName1": "Value1",
      "ColumnName2": "Value2"
  }
  client.add(table_name="MyTable", rows=[new_row])
  ```

### 2. Customizing A2UI v0.8 Cards
Open `card_templates.py`:
- Call `create_record_card(surface_id, title, record_dict)` to render a single row.
- Add custom fields or component layouts using standard A2UI v0.8 components (`Card`, `Column`, `Row`, `Text`).

---

## Deployment to Google Cloud Run

Deploy the container directly to Cloud Run:

```bash
gcloud run deploy appsheet-a2a-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars APPSHEET_APP_ID="your-app-id",APPSHEET_ACCESS_KEY="your-key",APPSHEET_REGION="www.appsheet.com"
```
