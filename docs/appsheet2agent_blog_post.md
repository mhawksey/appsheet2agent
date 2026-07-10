# Bridging AppSheet and Gemini Enterprise: Building appsheet2agent with the Google Antigravity SDK

In the era of generative AI, connecting large language models (LLMs) to line-of-business applications is one of the most impactful workflows developers can build. However, exposing enterprise database systems to conversational interfaces poses significant challenges in security context propagation, visual layout presentation, and access control.

To solve this, I created **[appsheet2agent](https://github.com/mhawksey/appsheet2agent)**—a compiler and studio application designed to transform any AppSheet schema and documentation into a secure, stateful, and visually rich A2A (Agent-to-Agent) custom agent for **Gemini Enterprise**.

This project was carried out as part of the **Agentic Architect Sprint** for Google Developer Experts (GDEs). The sprint challenges developers to show the world what is possible when using Gemini 3.5 reasoning, parallel subagents, and multi-agent orchestration to dramatically reduce time-to-value without sacrificing user experience (UX).

This post walks through the architectural breakthroughs, technical details, and design decisions I made while building `appsheet2agent`.

---

## ⚡ The Starting Point: A2A and OAuth User Delegation

My work began by adapting the excellent baseline architecture from the **[alphasecio/google-a2a](https://github.com/alphasecio/google-a2a)** repository, which provides a clean implementation of the Agent-to-Agent (A2A) protocol.

However, business databases demand strict security. I could not rely on a shared system-level service account to read and write records; every transaction had to execute strictly under the credentials of the user chatting with the model. To support this, I implemented **user delegation**:
1. Gemini Enterprise passes the corporate user's Google OAuth access token (`ya29.`) within the HTTP headers of every request.
2. The agent extracts this token and attaches it to AppSheet API calls using the `RunAsUserEmail` headers, enforcing row-level security and auditing.

---

## 🚀 Architectural Breakthrough: Why Cloud Run is Essential

During initial architectural testing, I attempted to host the agent using the native Google Cloud Vertex AI Reasoning Engine (also known as Agent Engine). However, I made a critical discovery:
* **The Constraint**: Vertex AI Reasoning Engine abstracts away the raw HTTP layer. When it receives a request, it strips out or overwrites incoming `Authorization` headers, replacing them with internal IAM project-level tokens. This breaks downstream OAuth propagation.
* **The Solution**: I bypassed Reasoning Engine in favour of deploying raw ASGI Starlette applications on **Google Cloud Run**. By running on Cloud Run, I maintained full HTTP control. A custom middleware validates the opaque Google OAuth tokens and stores them in a thread-safe `contextvars.ContextVar`, ensuring the user's identity is safely propagated to the database client.

For a detailed technical layout of this authentication flow, see the local guide on **[OAuth A2A Agent Integration](file:///Users/mhawksey/Documents/Antigravity%20Agents/google-a2a/docs/oauth_a2a_agent_guide.md)**.

---

## 🤖 Harnessing the Google Antigravity SDK (`google.antigravity`)

To manage the agent's internal execution loop, tool signatures, and security guardrails, I integrated the **Google Antigravity SDK (`google.antigravity`)**. 

The SDK allows me to bind AppSheet endpoints directly as tools:
1. **Dynamic Tool Generation**: The compiler parses the AppSheet OpenAPI schema and generates native Python `@tool` functions for CRUD operations (e.g. `find_tasks`, `add_tasks`, `edit_tasks`).
2. **Full Signature Exposure**: To ensure A2UI form events bind correctly, I expose the complete column schemas as tool arguments. This allows fields like primary keys (`TaskID`) and status values (`Status`) to be updated dynamically during model-guided tool invocations.
3. **Declarative Security Policies**: To prevent prompt injection and restrict data manipulation, I enforced a zero-trust policy directly in the Antigravity hook layer:
   ```python
   # Declarative security policy rule setup
   hooks.policy = "deny(*), allow(find_*), ask_user(add_*), ask_user(edit_*)"
   ```
   This guarantees that search operations execute seamlessly, while mutations require explicit user confirmation.

---

## 🎨 Visual Interface: Mapping A2UI v0.8 to AppSheet UX

Rather than returning plain markdown text, my agent generates visual interactive cards inside Gemini Enterprise using the **A2UI v0.8 Specification**. 

To mirror the visual layouts of the native AppSheet client, I integrated documentation parsing and UX heuristics:
* **PDF Schema Preprocessing**: The compiler preprocesses the application's `Application Documentation.pdf` file to extract UX column metadata (e.g. fields marked as `Hidden` or designated as the table `Label`).
* **UX Prioritisation & Hidden Column Filtering**: The generated executor runs a `format_records_for_ux()` helper function. It strips away system columns (like `_RowNumber` or `Row ID`) and reorders fields so that designated `Label` columns are placed first and rendered as card headers.
* **Automatic Record Sorting**: The preprocessor extracts views metadata—such as `SortBy` and `GroupBy` properties—from the PDF. The executor automatically sorts lists of records (such as sorting `Users` by `Name` ascending) to match the visual ordering of the native AppSheet client.
* **Dynamic Forms**: When a user asks to add or edit a record, the agent intercepts the intent and renders an A2UI form card containing input components (like text fields, checkboxes, and date pickers). On submission, it maps client actions (`submit_add_*` and `submit_edit_*`) to local tool functions to complete the transaction.

For more details on formatting visual components, see the local guide on **[AppSheet A2A Boilerplate Layouts](file:///Users/mhawksey/Documents/Antigravity%20Agents/google-a2a/docs/appsheet_a2a_boilerplate_guide.md)**.

---

## 📈 Development Milestones & Project Skills

The creation of `appsheet2agent` was marked by key developmental milestones:
1. **Starlette Middleware Capture**: Resolving JWT token propagation on Cloud Run.
2. **Metadata Integration**: Parsing PDFs to build prioritised layout schemas.
3. **End-to-End Interactivity Integration Tests**: Writing a test harness to mock JWT checks and verify LLM function calls against live Vertex AI.
4. **Edit Operations & View Sorting**: Supporting write/edit events and sorting lists using view metadata.
5. **Clean Public Sync Workflow**: Setting up a GitHub Actions workflow to selectively publish clean template versions to my public repository whenever a release tag (e.g. `v0.1`) is pushed.

Throughout the project, I drew upon several local and global **Agent Skills**:
* **`a2a-a2ui-oauth-integration`**: Guided token verification and A2UI card construction.
* **`google-antigravity-sdk`**: Provided orchestration patterns for multi-agent loops and Vertex AI model invocation.
* **Agent Platform ADK Skills**: Governed project scaffolding, local evaluation parameters, and Cloud Run target configurations.

---

## 🏁 Summary

By combining the A2A protocol, Google Cloud Run middleware, the Google Antigravity SDK, and the A2UI v0.8 card specification, `appsheet2agent` delivers a secure, state-of-the-art developer bridge. It allows complex enterprise apps to be translated instantly into intuitive, interactive Gemini Enterprise experiences.

Check out the public codebase and deploy your first agent today at **[github.com/mhawksey/appsheet2agent](https://github.com/mhawksey/appsheet2agent)**!

***

*Google Cloud credits are provided for this project.*

#AgenticArchitect #GoogleAntigravity
