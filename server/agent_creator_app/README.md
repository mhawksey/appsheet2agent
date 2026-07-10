# AppSheet Agent Creator Web Application

This web application enables non-technical or domain business creators to upload their AppSheet `openapi.json` specification and application documentation, test their agent live with an interactive **A2UI v0.8 card renderer**, and generate **Google Antigravity SDK (`google-antigravity`)** agent packages complete with **ARD (Agent Registration Definition)** specs and **Gemini Enterprise Admin Registration JSON**.

---

## Key Features

1. **OpenAPI 3.0 & PDF Documentation Preprocessor**:
   - Parses tables, actions, and schemas from `openapi.json`.
   - Programmatically extracts and parses AppSheet UX metadata (such as `Hidden` and `Label` column settings) from `Application Documentation.pdf` using a token-optimized preprocessor to prevent truncation.

2. **OAuth Delegation (`RunAsUserEmail`)**:
   - All generated agents automatically enforce `RunAsUserEmail` on all AppSheet API calls using the user's OAuth identity context.

3. **Dynamic A2UI v0.8 Layouts (No Table Constraint)**:
   - Lists of multiple records are dynamically formatted into vertical stacks of `Card` components, completely bypassing the unsupported `"Table"` component constraint of A2UI v0.8.
   - Utilizes a self-contained **A2UI Compatibility Matrix** (`compatibility_matrix.py`) to map AppSheet types securely without local file lookups.

4. **UX Prioritization & Column Filtering**:
   - Automatically filters out internal or hidden system columns (like `_RowNumber` or `Row ID`).
   - Prioritizes designated `Label` columns (like `Name` or `PlanName`) at the front of dictionaries, automatically displaying label values as the primary headlines of record list items.

5. **A2UI Form Generation & Interactivity Interception**:
   - **`create_form_card`**: Maps AppSheet columns directly to standard input fields (`TextField`, `CheckBox`, `DateTimeInput`, `MultipleChoice`).
   - **Interception**: Queries like `"add <table_name>"` are intercepted at the beginning of the execution loop to immediately render the form.
   - **Signature Binding**: On form submission client events (`userAction`), binds fields dynamically using `inspect.signature` to invoke the correct python tool.

6. **ARD Specification & Gemini Registration JSON**:
   - Generates `ard.json` conforming to the [ARD Specification](https://github.com/ards-project/ard-spec) and outputs copy-paste Registration JSON for the Gemini Enterprise Admin Console.

---

## Google Antigravity SDK Integration

The creator design sandbox uses the **Google Antigravity SDK (`google-antigravity`)** to run a stateful, autonomous Specialist Agent Architect. Inside [specialist_agent.py](file:///Users/mhawksey/Documents/Antigravity%20Agents/google-a2a/server/agent_creator_app/app/specialist_agent.py), this integration facilitates the interactive design interview:

### 1. Stateful Configuration (`LocalAgentConfig`)
The agent's stateful environment is managed via `LocalAgentConfig`:
- **Model Target**: Binds to `"gemini-3.5-flash"`.
- **GCP Authentication Context**: Optionally targets Google Vertex AI (`vertex=True`) by mapping the user's AppSheet region (e.g. `eu.appsheet.com` to `eu` location, or `www.appsheet.com` to `global` location) or falls back to direct API keys (`api_key`).
- **Session Persistence**: Passes the current `conversation_id` and registers `save_dir` (`~/.gemini/antigravity/brain/conversations`) to persist and resume the chat thread state across HTTP requests.

### 2. Sandbox Tool Binding
To enable the LLM agent to gather context dynamically from the parsed AppSheet database and documentation, the Antigravity Agent is equipped with local functions as tools:
- `get_app_table_schemas()`: Resolves table lists and columns parsed from `openapi.json`.
- `get_sample_rows_for_table(table_name)`: Reads real sample rows from the database.
- `search_application_docs(query)`: Searches through the PDF application documentation.

### 3. Execution Loop
The agent runs in an asynchronous context manager:
```python
from google.antigravity import Agent, LocalAgentConfig

# Setup config...
config = LocalAgentConfig(...)

async with Agent(config=config) as agent:
    response = await agent.chat(user_prompt)
    text_content = await response.text()
```
The agent responds with a structured JSON block containing the greeting text, suggested A2UI commands, detected capabilities, and generated Python tool helper code.

---

## Project Structure

```
server/agent_creator_app/
├── app/
│   ├── agent_generator.py      # Executor package compiler & template engine
│   ├── specialist_agent.py     # Specialist Agent Architect Sandbox loop
│   ├── openapi_parser.py       # OpenAPI spec parsing & validation
│   ├── pdf_preprocessor.py     # Token-optimized PDF parser (extracts UX rules)
│   ├── compatibility_matrix.py # Static type-to-A2UI component matrix mapping
│   └── main.py                 # FastAPI web application endpoint
├── static/
│   ├── index.html              # Creator Studio Dashboard frontend UI
│   └── app.js                  # Frontend client engine (A2UI renderer)
├── test_creator_app.py         # Creator Web App core unit tests
└── test_generated_agent_interactivity.py # Live Vertex AI Integration test suite
```

---

## Local Development & Run

### 1. Installation

Install dependencies using `uv` (recommended) or `pip`:
```bash
cd server/agent_creator_app
uv pip install -r requirements.txt
```

### 2. Run Web Dashboard

Start the FastAPI application:
```bash
uvicorn app.main:app --reload --port 8000
```
Open `http://localhost:8000` in your web browser.

### 3. Running Verification Tests

Run core unit tests (schema parsing, specialist architect flows):
```bash
uv run python test_creator_app.py
```

Run end-to-end integration tests using live **Vertex AI** (`gemini-3.5-flash` in project `a2ui-ge` with forced function calling) to verify client events, forms rendering, database tool binding, and strict A2UI mimeType (`application/json+a2ui`) schemas:
```bash
uv run python test_generated_agent_interactivity.py
```

---

## Deploy to Cloud Run

Deploy the containerized FastAPI application:
```bash
gcloud run deploy appsheet-agent-creator \
  --source ./server/agent_creator_app \
  --region europe-west1 \
  --allow-unauthenticated
```
