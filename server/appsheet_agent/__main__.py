"""
Starlette Application Entrypoint for AppSheet A2A Agent.

Includes AuthHeaderMiddleware to capture incoming Authorization headers,
populating the contextvar for execution downstream.
"""

import os
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, AgentExtension

from agent_executor import AppSheetAgentExecutor
from auth import auth_token_var

# Skills metadata definition
appsheet_skill = AgentSkill(
    id="appsheet_manage",
    name="AppSheet Manager",
    description="Query and update AppSheet application data on behalf of the logged in user.",
    tags=["appsheet", "database", "crud"],
    examples=["show records", "list tasks", "add record"],
)

_base_url = os.environ.get("AGENT_BASE_URL") or "https://placeholder-url.a.run.app"

# A2UI v0.8 Extension declaration
a2ui_extension = AgentExtension(
    uri="https://a2ui.org/a2a-extension/a2ui/v0.8",
    description="Ability to render A2UI cards in Gemini Enterprise",
    required=False,
    params={
        "supportedCatalogIds": [
            "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
        ]
    }
)

public_agent_card = AgentCard(
    name="appsheet_agent",
    description="AppSheet A2A Agent with OAuth RunAsUserEmail delegation and A2UI cards.",
    url=_base_url,
    iconUrl="https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/png/128/emoji_u1f4ca.png",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(
        streaming=False,
        extensions=[a2ui_extension]
    ),
    skills=[appsheet_skill],
    supports_authenticated_extended_card=True,
)

extended_agent_card = public_agent_card.model_copy(
    update={
        "name": "appsheet_agent",
        "description": "AppSheet A2A Agent with full OAuth authenticated data access.",
        "skills": [appsheet_skill],
    }
)

class AuthHeaderMiddleware:
    """Captures HTTP Authorization header and handles /healthz health probes."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            method = scope.get("method", "GET")
            if path in ("/healthz", "/health") and method == "GET":
                response_body = b'{"status": "ok", "agent": "appsheet_agent"}'
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(response_body)).encode("utf-8")),
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": response_body,
                })
                return

            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("latin1")
            auth_token_var.set(auth_header)
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)

request_handler = DefaultRequestHandler(
    agent_executor=AppSheetAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

server = A2AStarletteApplication(
    agent_card=public_agent_card,
    http_handler=request_handler,
    extended_agent_card=extended_agent_card,
)

app = AuthHeaderMiddleware(server.build())

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
