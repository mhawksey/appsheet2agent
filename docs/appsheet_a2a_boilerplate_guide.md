# AppSheet A2A Agent Boilerplate Guide

This guide details the architecture, configuration, and adaptation process for building AppSheet-integrated Agent-to-Agent (A2A) services for Gemini Enterprise using **Automatic OAuth User Delegation (`RunAsUserEmail`)** and **A2UI v0.8 visual cards**.

---

## 1. Architectural Motivation

When an agent interacts with an AppSheet application on behalf of an enterprise user, AppSheet security policies and row-level security expressions (such as `USEREMAIL()`) rely on the API request's `RunAsUserEmail` property.

By combining:
1. **Google OAuth Bearer Token Validation**: Extracting the authenticated user's identity (`email`) from their session token.
2. **AppSheet API Client**: Automatically populating `"Properties": {"RunAsUserEmail": user_email}` on all `Add`, `Edit`, `Delete`, `Find`, and `Action` requests.
3. **A2UI v0.8 Output**: Formatting response data into native Gemini Enterprise card components.

Team developers can ensure that all data changes and queries are fully audited and constrained by the user's specific permissions in AppSheet.

---

## 2. Configuration & Setup

### Environment Variables (`.env`)

Configure the agent's target AppSheet application in `.env`:

```ini
# AppSheet API Credentials
APPSHEET_APP_ID=5a3b9f48-xxxx-xxxx-xxxx-xxxxxxxxxxxx
APPSHEET_ACCESS_KEY=V2-bA2SK-xxxx-xxxx-xxxx

# Region Configuration (e.g. www.appsheet.com, eu.appsheet.com)
APPSHEET_REGION=www.appsheet.com

# Default Target Table Name
APPSHEET_DEFAULT_TABLE=Tasks

# Server Settings
AGENT_BASE_URL=https://appsheet-agent-xyz-uc.a.run.app
PORT=8080
```

---

## 3. How Automatic Delegation (`RunAsUserEmail`) Works

1. **Header Interception**: `AuthHeaderMiddleware` in `__main__.py` captures incoming HTTP `Authorization` headers and sets a thread-isolated `contextvars.ContextVar`.
2. **Identity Verification**: `agent_executor.py` validates the token (using Google's `userinfo` endpoint for `ya29.` opaque tokens or OIDC JWKS) and retrieves `user_email`.
3. **API Client Injection**: `AppSheet(user_email=user_email)` merges `RunAsUserEmail` into every outbound HTTP payload:

```json
{
  "Action": "Find",
  "Properties": {
    "RunAsUserEmail": "alice@company.com"
  },
  "Rows": []
}
```

---

## 4. Adapting the Boilerplate for Custom Apps

### Step 1: Define Your Table Schema
In `agent_executor.py`, customize your table operations to match your AppSheet app's schema:

```python
# Adding a record to a custom table
new_task = {
    "TaskID": str(uuid.uuid4()),
    "TaskName": "Review Quarterly Q3 Report",
    "AssignedTo": user_email,
    "Status": "Pending"
}
result = client.add(table_name="Tasks", rows=[new_task])
```

### Step 2: Customize A2UI v0.8 Visual Cards
In `card_templates.py`, use the modular generators to format record views:

```python
from card_templates import create_record_card

# Generates A2UI v0.8 layout array
card_commands = create_record_card(
    surface_id="task-detail-card",
    title="Task Details",
    record_data=record_dict
)
```

---

## 5. Deployment to Google Cloud Run

Deploy your agent using Google Cloud Build / Cloud Run:

```bash
gcloud run deploy appsheet-a2a-agent \
  --source ./server/appsheet_agent \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars APPSHEET_APP_ID="YOUR_APP_ID",APPSHEET_ACCESS_KEY="YOUR_KEY",APPSHEET_REGION="www.appsheet.com"
```
