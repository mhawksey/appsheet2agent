# Project Rules: Google A2A with OAuth and A2UI v0.8

This project contains a Gemini Enterprise A2A agent deployed on Cloud Run, explicitly configured to securely receive user Google OAuth tokens and render A2UI v0.8 cards. Any agents working on this project must adhere to the following rules:

1. **Architecture Constraint - Cloud Run**: Do NOT attempt to migrate this project to Vertex AI Reasoning Engine (Agent Engine). This project requires raw ASGI HTTP access to intercept the `Authorization` header containing the user's opaque Google access token. Agent Engine abstracts the HTTP layer and overwrites the `Authorization` header with internal IAM tokens, which breaks OAuth token propagation.

2. **Middleware Token Extraction**: Token extraction must be performed before the request reaches the A2A SDK. A Starlette middleware captures the `Authorization` header and stores it in a `contextvars.ContextVar` named `auth_token_var`. You must retrieve the token from this variable in your `AgentExecutor` implementations.

3. **Google Token Validation**: Opaque Google tokens (starting with `ya29.`) cannot be validated with standard JWKS. They must be validated against the Google `userinfo` endpoint (`https://www.googleapis.com/oauth2/v3/userinfo`). Use the `validate_jwt` function provided in `auth.py` for all authentication validation.

4. **A2UI v0.8 Structure**: When generating A2UI layout cards, you must strictly use the v0.8 specification format.
    - The layout must be an array of rendering commands (e.g., `beginRendering`, `surfaceUpdate`).
    - The A2A Python SDK `DataPart` requires a single dictionary. Do NOT pass the entire array into a single `DataPart`. You must yield a separate `DataPart` for each rendering command in the array.
    - Every `DataPart` wrapping a card command must include `"mimeType": "application/json+a2ui"` in its metadata.

5. **Agent Capabilities**: When modifying capabilities, ensure that the extensions array references the correct v0.8 catalog (`https://a2ui.org/specification/v0_8/standard_catalog_definition.json`). Streaming mode (`True` or `False`) must be consistent with the Gemini Agent Registry configuration.

6. **Milestone Selective Publishing**: This project is configured to selectively publish production milestones and clean template versions to the public repository [mhawksey/appsheet2agent](https://github.com/mhawksey/appsheet2agent) using the GitHub Actions workflow defined in `.github/workflows/publish-public.yml`.
    - Do NOT publish every commit to the public repo. Publishing is strictly version/milestone-driven.
    - To publish, tag a release version with `v*` (e.g. `v1.0.0`) and push it: `git tag v1.0.0 && git push origin v1.0.0`.
    - Manual dispatch can also be triggered from the Actions UI.
    - Requires a GitHub Personal Access Token saved as repository secret `PUBLIC_REPO_TOKEN` in the private repository.
    - Only the clean core logic (`agent_creator_app`, `appsheet_agent`), standard `README.md`, `LICENSE`, and `.gitignore` are synced; local environment directories (`.venv`, `__pycache__`) are excluded.

Read the `a2a-a2ui-oauth-integration` skill (`skills/a2a_a2ui_integration/SKILL.md`) for detailed examples and further documentation.
