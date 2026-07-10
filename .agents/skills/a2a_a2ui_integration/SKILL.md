---
name: a2a-a2ui-oauth-integration
description: Guidelines for building, authenticating, and rendering A2UI v0.8 cards inside Gemini Enterprise using Cloud Run A2A agents.
---

# A2A / A2UI v0.8 Integration with Gemini Enterprise & Google OAuth

This skill documents key findings, architectural patterns, and troubleshooting steps for successfully integrating Agent-to-Agent (A2A) agents with **Gemini Enterprise** client platform using **A2UI v0.8** cards and **Google OAuth access tokens**.

---

## 1. Google OAuth Token Validation
* **The Problem**: Gemini Enterprise A2A agents receive the client user's Google authentication token in the `Authorization` header. Unlike Microsoft AD tokens which are JWTs and can be validated locally via JWKS, Google tokens for end users are opaque strings (starting with `ya29.`).
* **The Fix**: Detect Google opaque tokens and validate them using Google's userinfo endpoint:
  ```python
  if token.startswith("ya29."):
      # Opaque Google Access Token
      response = requests.get(
          "https://www.googleapis.com/oauth2/v3/userinfo",
          headers={"Authorization": f"Bearer {token}"}
      )
      response.raise_for_status()
      claims = response.json()
      # claims contains 'email', 'picture', etc.
  ```

---

## 2. A2UI v0.8 Card Structure
* **The Problem**: Gemini Enterprise currently only supports **A2UI version v0.8**. The newer v0.9+ layout format (a single `components` dictionary using `"type": "Card"`) will fail to render.
* **The Fix**: The layout must be structured as an array of rendering command dictionaries (such as `beginRendering`, `surfaceUpdate`, and `dataModelUpdate`):
  ```json
  [
    {
      "beginRendering": {
        "surfaceId": "my-card-id",
        "root": "my_root_component"
      }
    },
    {
      "surfaceUpdate": {
        "surfaceId": "my-card-id",
        "components": [
          {
            "id": "my_root_component",
            "component": {
              "Card": { "child": "my_content_text" }
            }
          },
          {
            "id": "my_content_text",
            "component": {
              "Text": { "text": { "literalString": "Hello v0.8!" } }
            }
          }
        ]
      }
    }
  ]
  ```

---

## 3. DataPart Wrapping Requirements
* **The Problem**: In the A2A Python SDK, the `DataPart` model requires the `data` field to be a dictionary, not a list.
* **The Fix**: Loop through the list of rendering commands and wrap **each command dictionary separately** in its own `DataPart` inside the message `parts` list, ensuring `"mimeType": "application/json+a2ui"` is specified in each DataPart's metadata:
  ```python
  parts = [
      Part(root=TextPart(text="Response text...")),
      *[Part(root=DataPart(
          data=cmd,
          metadata={"mimeType": "application/json+a2ui"}
      )) for cmd in a2ui_layout_list]
  ]
  ```

---

## 4. Agent capabilities declaration
* **Streaming**: Set `"streaming": true` or `"streaming": false` in both the agent's capabilities card registration and the code card capabilities configuration. Gemini Enterprise supports both streaming and non-streaming modes.
* **Extensions Catalog URI**: The catalog parameter in the Capabilities definition must use the exact schema definition URL for standard v0.8 catalogs:
  ```json
  "supportedCatalogIds": [
      "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
  ]
  ```
