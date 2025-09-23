# MCP Client Discovery Manager Result

This document describes the general structure of the JSON response returned by the MCP Client Discovery Manager.
The discovery result provides two main sections: `tools` and `resources`.

---

## JSON Structure

```json
{
  "tools": {
    "<tool_namespace>": [
      {
        "name": "<string>",                // Tool name
        "description": "<string>",         // Short description of the tool
        "inputSchema": {                   // JSON schema for tool input
          "type": "object",
          "properties": {
            "<param_name>": {
              "title": "<string>",
              "type": "<string | integer | array>"
            }
          },
          "required": ["<param_name>"]     // List of required parameters
        }
      }
    ]
  },
  "resources": {
    "<resource_namespace>": [
      {
        "uri": "<string>",                 // Resource URI
        "name": "<string>",                // Resource name
        "description": "<string>"          // Short description of the resource
      }
    ]
  }
}
```

## Explanation
- `tools`:
  A collection of tool definitions, grouped by namespace. Each tool defines its name, description, and an inputSchema describing the required input format.
- `resources`:
  A collection of available resources, also grouped by namespace. Each resource includes a unique uri, name, and description.

### Example

```json
{
  "tools": {
    "knowledge_bases_mcp": [
      {
        "name": "greeting",
        "description": "Greet a person with their name.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "name": { "title": "Name", "type": "string" }
          },
          "required": ["name"]
        }
      }
    ]
  },
  "resources": {
    "knowledge_bases_mcp": [
      {
        "uri": "resource:/list/sample",
        "name": "Sample Resource",
        "description": "A sample static resource"
      }
    ]
  }
}

```