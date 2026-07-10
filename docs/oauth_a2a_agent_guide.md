# Building OAuth-Enabled A2A Agents for Gemini Enterprise

This technical guide outlines the architecture, code patterns, and deployment strategies for building Agent-to-Agent (A2A) services that securely receive Google OAuth tokens from Gemini Enterprise users and render rich A2UI v0.8 cards.

## 1. Architecture: Cloud Run vs. Agent Engine

When building A2A agents that require the end-user's Google OAuth token (for example, to access personalized data via a Google API on the user's behalf), you must deploy to **Cloud Run**, rather than using the fully managed **Vertex AI Reasoning Engine** (Agent Engine).

### The Agent Engine Limitation
Agent Engine operates behind a managed gateway that abstracts the HTTP layer from your execution code. During this process:
1. **Header Stripping**: The original `Authorization` header containing the user's Google OAuth token is overwritten by Vertex AI's internal IAM tokens used for service-to-service authentication.
2. **Body Parameter Filtering**: Raw body parameters where the client might inject credentials (like the `authorizations` block in the JSON-RPC request) are often stripped or rendered inaccessible to the underlying SDK execution context.

This makes securely propagating end-user OAuth tokens nearly impossible on Agent Engine without highly customized, unsupported workarounds.

### The Cloud Run Advantage
Deploying a FastAPI/Starlette application directly to **Cloud Run** exposes the raw ASGI/HTTP stack to your application. This allows you to deploy custom middleware that intercepts the JSON-RPC payload or HTTP headers to securely extract the user's opaque Google access token (`ya29...`) *before* the A2A SDK abstraction drops it.

---

## 2. Extracting the OAuth Token (Middleware)

To extract the Google OAuth token in a Cloud Run deployment, we use Starlette middleware and Python's `contextvars` to make the token available globally within the async execution context.

```python
# __main__.py
import contextvars
from a2a.server.apps import A2AStarletteApplication

# Create a ContextVar to store the token for the current request lifecycle
auth_token_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "auth_token", default=""
)

class AuthHeaderMiddleware:
    """Captures and stores the Authorization header before SDK processing."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            # Extract the raw authorization header
            auth_header = headers.get(b"authorization", b"").decode("latin1")
            auth_token_var.set(auth_header)
            
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)

# Wrap your A2A server application with the middleware
# app = AuthHeaderMiddleware(server.build())
```

Inside your `AgentExecutor`'s `execute` method, you can retrieve the token seamlessly:

```python
# agent_executor.py
from auth import auth_token_var

async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
    # Safely get the token extracted by the middleware
    token = auth_token_var.get().removeprefix("Bearer ").strip()
    
    # Optional fallback: Look into the JSON-RPC metadata block if the token 
    # was passed explicitly in the payload authorizations array.
    if not token and context.metadata:
        token = context.metadata.get("authorization", "").removeprefix("Bearer ").strip()
        
    if not token:
        # Yield authentication required state
        return
```

---

## 3. Validating Google Opaque Tokens

Unlike Microsoft Active Directory tokens which are standard JWTs that can be validated locally via JWKS, end-user Google tokens are often opaque strings starting with `ya29.`. These must be validated against Google's `userinfo` endpoint.

```python
# auth.py
import urllib.request
import json
import jwt

def validate_jwt(token: str) -> dict:
    """Validates a Bearer JWT or Google access token."""
    if token.startswith("ya29."):
        # Opaque Google Access Token Validation
        try:
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode()) # Contains 'email', 'picture', etc.
        except Exception as e:
            raise jwt.PyJWTError(f"Invalid Google access token: {e}")

    # Fallback to standard JWKS validation for other identity providers
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token, signing_key.key, algorithms=["RS256"],
        audience=OAUTH_AUDIENCE, issuer=OAUTH_ISSUER,
    )
```

---

## 4. Returning A2UI v0.8 Cards

Gemini Enterprise strictly requires **A2UI v0.8**. Attempting to use the simplified v0.9 layout structure (e.g., a single `components` dictionary) will result in a rendering failure.

### Key Requirements for Gemini Enterprise A2UI:
1. **Command Array Structure**: The layout must be a list of explicit rendering commands: `beginRendering`, `surfaceUpdate`, and optionally `dataModelUpdate`.
2. **Individual DataParts**: The Python A2A SDK's `DataPart` model expects a dictionary, not a list. Therefore, you must iterate over your array of commands and yield a distinct `DataPart` for each one.
3. **MimeType Metadata**: Each `DataPart` must explicitly specify `"mimeType": "application/json+a2ui"` in its metadata.

### Implementation Example

```python
# agent_executor.py
from a2a.types import Part, TextPart, DataPart
from a2a.utils import new_agent_parts_message

# 1. Define the A2UI v0.8 array of commands
a2ui_layout_commands = [
    {
        "beginRendering": {
            "surfaceId": "dice-roll-card",
            "root": "roll_card"
        }
    },
    {
        "surfaceUpdate": {
            "surfaceId": "dice-roll-card",
            "components": [
                {
                    "id": "roll_card",
                    "component": { "Card": { "child": "roll_text" } }
                },
                {
                    "id": "roll_text",
                    "component": {
                        "Text": {
                            "text": { "literalString": "Hello Gemini Enterprise!" },
                            "usageHint": "body"
                        }
                    }
                }
            ]
        }
    }
]

# 2. Iterate and wrap each dictionary command in its own DataPart
parts = [
    Part(root=TextPart(text="Here is your card:")),
    *[
        Part(root=DataPart(
            data=command_dict,
            metadata={"mimeType": "application/json+a2ui"}
        )) 
        for command_dict in a2ui_layout_commands
    ]
]

# 3. Enqueue the parts message
msg = new_agent_parts_message(
    parts=parts,
    context_id=context.context_id,
    task_id=context.task_id,
)
await event_queue.enqueue_event(msg)
```

---

## 5. Deployment & Configuration Speed-Up Tips

* **Local Validation**: Avoid long deployment cycles. Test token extraction and payload wrapping locally using the `uvicorn` dev server and crafting curl requests with mocked `Authorization` headers.
* **Pre-Bundling JSON Assets**: Hardcoding massive nested A2UI JSON structures in Python can be error-prone. Place your base `card.json` structures in your codebase, load them with `json.load()` at runtime, and yield the parts dynamically. This ensures valid JSON and speeds up iteration.
* **Agent Capabilities Registration**: Explicitly state `"streaming": false` (or `true`) in your `AgentCapabilities` definition. Gemini Enterprise supports both, but consistency between your code configuration and the Gemini Agent Registry is crucial.
* **Catalog URI**: Ensure your extension declaration references the standard v0.8 catalog exactly: 
  `https://a2ui.org/specification/v0_8/standard_catalog_definition.json`.
