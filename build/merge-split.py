#!/usr/bin/env python3
"""
Produce per-group UiPath-importable OpenAPI 3.0 specs from Snowflake REST API sources.

Strategy: each output file is self-contained with additionalProperties:true for all
request/response bodies. This mirrors the working cortex-generic-openai connector.
No cross-file $refs, no allOf, no discriminator.

Output: ~/projects/snowflake-rest-api-specs/uipath-ready/split/
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

SPECS_DIR = Path("/home/ubuntu/projects/snowflake-rest-api-specs/specifications")
OUT_DIR = Path("/home/ubuntu/projects/snowflake-rest-api-specs/uipath-ready/split")

# ---------------------------------------------------------------------------
# Shared building blocks (copied into every output spec)
# ---------------------------------------------------------------------------

SERVERS = [
    {
        "url": "https://{account}.snowflakecomputing.com",
        "description": "Snowflake account endpoint",
        "variables": {
            "account": {
                "default": "MDTPLC-AWSUSE1P1",
                "description": (
                    "Snowflake account identifier (e.g. MDTPLC-AWSUSE1P1). "
                    "No '.snowflakecomputing.com' suffix."
                ),
                "x-ms-connection-parameter": {
                    "name": "account",
                    "uiDefinition": {
                        "displayName": "Snowflake Account",
                        "description": (
                            "Your Snowflake account identifier (e.g. MDTPLC-AWSUSE1P1)"
                        ),
                        "tooltip": (
                            "Find under Admin > Accounts or run "
                            "SELECT CURRENT_ACCOUNT() in Snowflake"
                        ),
                        "constraints": {"required": "true"},
                    },
                },
            }
        },
    }
]

SECURITY_SCHEMES = {
    "SnowflakeOAuth": {
        "type": "oauth2",
        "description": (
            "Snowflake OAuth 2.0 Authorization Code. "
            "Configure client ID/secret from your Snowflake OAuth integration. "
            "Scope: session:role:<ROLE>."
        ),
        "flows": {
            "authorizationCode": {
                # Static URLs required by UiPath converter validation
                "authorizationUrl": "https://orgname-accountname.snowflakecomputing.com/oauth/authorize",
                "tokenUrl": "https://orgname-accountname.snowflakecomputing.com/oauth/token-request",
                "refreshUrl": "https://orgname-accountname.snowflakecomputing.com/oauth/token-request",
                # x-ms-* overrides used at runtime — support {account} interpolation
                "x-ms-authorization-url": "https://{account}.snowflakecomputing.com/oauth/authorize",
                "x-ms-token-url": "https://{account}.snowflakecomputing.com/oauth/token-request",
                "x-ms-refresh-url": "https://{account}.snowflakecomputing.com/oauth/token-request",
                "x-ms-revoke-url": "https://{account}.snowflakecomputing.com/oauth/token-revoke",
                "x-tokenRevocationUrl": "https://orgname-accountname.snowflakecomputing.com/oauth/token-revoke",
                "scopes": {
                    "session:role:PUBLIC": "Access Snowflake with the PUBLIC role",
                },
                "x-ms-connection-parameter": {
                    "name": "token",
                    "uiDefinition": {
                        "displayName": "OAuth Scope",
                        "description": "Snowflake session scope. Format: session:role:<ROLE_NAME>",
                        "tooltip": "Enter the role you want to use, e.g. session:role:MY_ROLE",
                        "constraints": {"required": "true"},
                    },
                },
            }
        },
    }
}

SF_PARAMS: dict = {
    "SnowflakeAuthorizationTokenType": {
        "name": "X-Snowflake-Authorization-Token-Type",
        "in": "header",
        "required": True,
        "description": (
            "Snowflake authorization token type. For OAuth use OAUTH; "
            "for PAT use PROGRAMMATIC_ACCESS_TOKEN."
        ),
        "x-ms-visibility": "advanced",
        "x-ms-summary": "Token Type",
        "schema": {
            "type": "string",
            "enum": ["OAUTH", "PROGRAMMATIC_ACCESS_TOKEN", "KEYPAIR_JWT"],
            "default": "OAUTH",
        },
    },
    "SnowflakeRole": {
        "name": "X-Snowflake-Role",
        "in": "header",
        "required": False,
        "description": "Snowflake role to use for the request.",
        "x-ms-visibility": "advanced",
        "x-ms-summary": "Role",
        "schema": {"type": "string", "default": "DEV_FDH_PROJ_MGMT_RW"},
        "x-ms-connection-parameter": {
            "name": "role",
            "uiDefinition": {
                "displayName": "Default Role",
                "description": "Default role sent with every request unless overridden per-call.",
                "constraints": {"required": "false"},
            },
        },
    },
    "SnowflakeWarehouse": {
        "name": "X-Snowflake-Warehouse",
        "in": "header",
        "required": False,
        "description": "Snowflake warehouse to use.",
        "x-ms-visibility": "advanced",
        "x-ms-summary": "Warehouse",
        "schema": {"type": "string", "default": "AGENT_WH"},
        "x-ms-connection-parameter": {
            "name": "warehouse",
            "uiDefinition": {
                "displayName": "Default Warehouse",
                "description": "Default warehouse sent with every request unless overridden per-call.",
                "constraints": {"required": "false"},
            },
        },
    },
    "SnowflakeDatabase": {
        "name": "X-Snowflake-Database",
        "in": "header",
        "required": False,
        "description": "Default Snowflake database context.",
        "x-ms-visibility": "advanced",
        "x-ms-summary": "Default Database",
        "schema": {"type": "string", "default": "DEV_FDH_DB"},
        "x-ms-connection-parameter": {
            "name": "database",
            "uiDefinition": {
                "displayName": "Default Database",
                "description": "Default database sent with every request unless overridden per-call.",
                "constraints": {"required": "false"},
            },
        },
    },
    "SnowflakeSchema": {
        "name": "X-Snowflake-Schema",
        "in": "header",
        "required": False,
        "description": "Default Snowflake schema context.",
        "x-ms-visibility": "advanced",
        "x-ms-summary": "Default Schema",
        "schema": {"type": "string", "default": "PROJ_MGMT"},
        "x-ms-connection-parameter": {
            "name": "schema",
            "uiDefinition": {
                "displayName": "Default Schema",
                "description": "Default schema sent with every request unless overridden per-call.",
                "constraints": {"required": "false"},
            },
        },
    },
}

SF_PATH_PARAMS = [
    {"$ref": f"#/components/parameters/{name}"}
    for name in SF_PARAMS
]

GENERIC_BODY = {"type": "object", "additionalProperties": True}

# ---------------------------------------------------------------------------
# MANUAL_PATHS (Cortex Agents — hand-built, no source spec file)
# ---------------------------------------------------------------------------

MANUAL_PATHS: dict = {
    "/api/v2/cortex/threads": {
        "post": {
            "operationId": "createThread",
            "x-ms-summary": "Create Thread",
            "summary": "Create a new conversation thread",
            "tags": ["Cortex Agents"],
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "origin_application": {
                                    "type": "string",
                                    "x-ms-summary": "Origin Application",
                                    "description": "App name that created the thread. Max 16 bytes.",
                                }
                            },
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Thread created",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "thread_id": {"type": "integer"},
                                    "thread_name": {"type": "string"},
                                    "origin_application": {"type": "string"},
                                    "created_on": {"type": "integer"},
                                    "updated_on": {"type": "integer"},
                                },
                            }
                        }
                    },
                }
            },
        }
    },
    "/api/v2/cortex/threads/{id}": {
        "get": {
            "operationId": "describeThread",
            "x-ms-summary": "Get Thread Messages",
            "summary": "Describe a thread and list its messages",
            "tags": ["Cortex Agents"],
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "description": "Thread UUID",
                    "x-ms-summary": "Thread ID",
                    "schema": {"type": "integer"},
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "required": False,
                    "description": "Number of messages per page (max 100)",
                    "x-ms-summary": "Page Size",
                    "schema": {"type": "integer", "default": 20, "maximum": 100},
                },
                {
                    "name": "last_message_id",
                    "in": "query",
                    "required": False,
                    "description": "Cursor: return messages after this message ID",
                    "x-ms-summary": "Last Message ID",
                    "schema": {"type": "integer"},
                },
            ],
            "responses": {
                "200": {
                    "description": "Thread metadata and messages",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "additionalProperties": True}
                        }
                    },
                }
            },
        }
    },
    "/api/v2/cortex/agent:run": {
        "post": {
            "operationId": "agentRun",
            "x-ms-summary": "Run Agent (Inline)",
            "summary": "Run a Cortex Agent without an agent object",
            "tags": ["Cortex Agents"],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["messages"],
                            "properties": {
                                "messages": {
                                    "type": "array",
                                    "x-ms-summary": "Messages",
                                    "items": {"type": "object", "additionalProperties": True},
                                    "description": "Conversation messages",
                                },
                                "stream": {
                                    "type": "boolean",
                                    "default": True,
                                    "description": "Stream response via SSE",
                                    "x-ms-summary": "Stream Response",
                                },
                                "thread_id": {
                                    "type": "integer",
                                    "description": "Optional thread ID for conversation continuity",
                                    "x-ms-summary": "Thread ID",
                                },
                                "parent_message_id": {
                                    "type": "integer",
                                    "description": "Optional parent message ID",
                                    "x-ms-summary": "Parent Message ID",
                                },
                                "tools": {
                                    "type": "array",
                                    "x-ms-summary": "Tools",
                                    "items": {"type": "object", "additionalProperties": True},
                                    "description": "Tools available to the agent",
                                },
                                "tool_resources": {
                                    "type": "object",
                                    "additionalProperties": True,
                                    "x-ms-summary": "Tool Resources",
                                    "description": "Resources for tools",
                                },
                                "tool_choice": {
                                    "type": "object",
                                    "additionalProperties": True,
                                    "x-ms-summary": "Tool Choice",
                                    "description": "Tool selection control",
                                },
                            },
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Agent response (SSE stream or JSON)",
                    "content": {
                        "text/event-stream": {"schema": {"type": "string"}},
                        "application/json": {
                            "schema": {"type": "object", "additionalProperties": True}
                        },
                    },
                }
            },
        }
    },
    "/api/v2/databases/{database}/schemas/{schema}/agents": {
        "post": {
            "operationId": "createAgent",
            "x-ms-summary": "Create Agent",
            "summary": "Create a Cortex Agent Object",
            "tags": ["Cortex Agents"],
            "parameters": [
                {"name": "database", "in": "path", "required": True, "x-ms-summary": "Database", "schema": {"type": "string"}},
                {"name": "schema", "in": "path", "required": True, "x-ms-summary": "Schema", "schema": {"type": "string"}},
                {
                    "name": "createMode",
                    "in": "query",
                    "required": False,
                    "x-ms-summary": "Create Mode",
                    "schema": {"type": "string", "enum": ["errorIfExists", "orReplace", "ifNotExists"]},
                },
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string", "x-ms-summary": "Agent Name"},
                                "comment": {"type": "string", "x-ms-summary": "Comment"},
                                "profile": {"type": "object", "additionalProperties": True, "x-ms-summary": "Profile"},
                                "models": {"type": "object", "additionalProperties": True, "x-ms-summary": "Models"},
                                "instructions": {"type": "object", "additionalProperties": True, "x-ms-summary": "Instructions"},
                                "orchestration": {"type": "object", "additionalProperties": True, "x-ms-summary": "Orchestration"},
                                "tools": {"type": "array", "items": {"type": "object", "additionalProperties": True}, "x-ms-summary": "Tools"},
                                "tool_resources": {"type": "object", "additionalProperties": True, "x-ms-summary": "Tool Resources"},
                            },
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Agent created",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "properties": {"status": {"type": "string"}}}
                        }
                    },
                }
            },
        }
    },
    "/api/v2/databases/{database}/schemas/{schema}/agents/{name}": {
        "get": {
            "operationId": "describeAgent",
            "x-ms-summary": "Get Agent",
            "summary": "Describe a Cortex Agent Object",
            "tags": ["Cortex Agents"],
            "parameters": [
                {"name": "database", "in": "path", "required": True, "x-ms-summary": "Database", "schema": {"type": "string"}},
                {"name": "schema", "in": "path", "required": True, "x-ms-summary": "Schema", "schema": {"type": "string"}},
                {"name": "name", "in": "path", "required": True, "x-ms-summary": "Agent Name", "schema": {"type": "string"}},
            ],
            "responses": {
                "200": {
                    "description": "Agent details",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "additionalProperties": True}
                        }
                    },
                }
            },
        },
        "delete": {
            "operationId": "deleteAgent",
            "x-ms-summary": "Delete Agent",
            "summary": "Delete a Cortex Agent Object",
            "tags": ["Cortex Agents"],
            "parameters": [
                {"name": "database", "in": "path", "required": True, "x-ms-summary": "Database", "schema": {"type": "string"}},
                {"name": "schema", "in": "path", "required": True, "x-ms-summary": "Schema", "schema": {"type": "string"}},
                {"name": "name", "in": "path", "required": True, "x-ms-summary": "Agent Name", "schema": {"type": "string"}},
            ],
            "responses": {
                "200": {
                    "description": "Agent deleted",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"status": {"type": "string", "description": "Agent successfully deleted."}},
                            }
                        }
                    },
                }
            },
        },
    },
    "/api/v2/databases/{database}/schemas/{schema}/agents/{name}:feedback": {
        "post": {
            "operationId": "agentFeedback",
            "x-ms-summary": "Submit Agent Feedback",
            "summary": "Collect feedback about a Cortex Agent response",
            "tags": ["Cortex Agents"],
            "parameters": [
                {"name": "database", "in": "path", "required": True, "x-ms-summary": "Database", "schema": {"type": "string"}},
                {"name": "schema", "in": "path", "required": True, "x-ms-summary": "Schema", "schema": {"type": "string"}},
                {"name": "name", "in": "path", "required": True, "x-ms-summary": "Agent Name", "schema": {"type": "string"}},
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["positive"],
                            "properties": {
                                "orig_request_id": {"type": "string", "x-ms-summary": "Original Request ID", "description": "Request ID for the message being rated"},
                                "positive": {"type": "boolean", "x-ms-summary": "Positive", "description": "True for positive feedback"},
                                "feedback_message": {"type": "string", "x-ms-summary": "Feedback Message"},
                                "categories": {"type": "array", "items": {"type": "string"}, "x-ms-summary": "Categories"},
                                "thread_id": {"type": "integer", "x-ms-summary": "Thread ID"},
                            },
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Feedback submitted",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "properties": {"status": {"type": "string"}}}
                        }
                    },
                }
            },
        }
    },
    "/api/v2/databases/{database}/schemas/{schema}/agents/{name}:run": {
        "post": {
            "operationId": "agentRunWithObject",
            "x-ms-summary": "Run Agent",
            "summary": "Run a Cortex Agent using a named Agent Object",
            "tags": ["Cortex Agents"],
            "parameters": [
                {"name": "database", "in": "path", "required": True, "x-ms-summary": "Database", "schema": {"type": "string"}},
                {"name": "schema", "in": "path", "required": True, "x-ms-summary": "Schema", "schema": {"type": "string"}},
                {"name": "name", "in": "path", "required": True, "x-ms-summary": "Agent Name", "schema": {"type": "string"}},
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["messages"],
                            "properties": {
                                "messages": {"type": "array", "x-ms-summary": "Messages", "items": {"type": "object", "additionalProperties": True}},
                                "stream": {"type": "boolean", "default": True, "x-ms-summary": "Stream Response"},
                                "thread_id": {"type": "integer", "x-ms-summary": "Thread ID"},
                                "parent_message_id": {"type": "integer", "x-ms-summary": "Parent Message ID"},
                                "tool_choice": {"type": "object", "additionalProperties": True, "x-ms-summary": "Tool Choice"},
                            },
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Agent response (SSE stream or JSON)",
                    "content": {
                        "text/event-stream": {"schema": {"type": "string"}},
                        "application/json": {
                            "schema": {"type": "object", "additionalProperties": True}
                        },
                    },
                }
            },
        }
    },
}

# ---------------------------------------------------------------------------
# Group definitions
# ---------------------------------------------------------------------------
# Each entry: (output_filename, title, version, description, source_spec_files_or_None_for_manual)
# source_spec_files: list of filenames from SPECS_DIR, or "MANUAL" for MANUAL_PATHS

SPLIT_GROUPS = [
    (
        "snowflake-cortex-analyst.yaml",
        "Snowflake Cortex Analyst API",
        "2.0.0",
        (
            "Snowflake Cortex Analyst — natural language to SQL. "
            "Endpoints: sendMessage, feedback, verifiedQuerySuggestions, "
            "fastGeneration, preSelection, filtersAndMetricsSuggestions, "
            "agenticOptimizations, token."
        ),
        ["cortex-analyst.yaml"],
    ),
    (
        "snowflake-cortex-search.yaml",
        "Snowflake Cortex Search API",
        "2.0.0",
        (
            "Snowflake Cortex Search — semantic search over structured data. "
            "Endpoints: list/create/get/delete search services, query, suggest, "
            "suspend, resume, feedback."
        ),
        ["cortex-search-service.yaml"],
    ),
    (
        "snowflake-cortex-inference.yaml",
        "Snowflake Cortex Inference API",
        "2.0.0",
        (
            "Snowflake Cortex LLM inference endpoints. "
            "Includes: inference:complete, inference:embed, /models list, "
            "OpenAI-compat chat/completions, Anthropic-compat messages."
        ),
        [
            "cortex-inference.yaml",
            "cortex-embed.yaml",
            "cortex-generic-openai.yaml",
            "cortex-generic-anthropic.yaml",
        ],
    ),
    (
        "snowflake-cortex-agents.yaml",
        "Snowflake Cortex Agents API",
        "2.0.0",
        (
            "Snowflake Cortex Agents — create/run/manage agent objects and threads. "
            "Endpoints: createThread, getThread, agentRun (inline), "
            "createAgent, getAgent, deleteAgent, runAgent, agentFeedback."
        ),
        ["MANUAL"],
    ),
    (
        "snowflake-sql-api.yaml",
        "Snowflake SQL API",
        "2.0.0",
        (
            "Snowflake SQL API — execute SQL statements asynchronously. "
            "Endpoints: submit statement, get results, cancel."
        ),
        ["sqlapi.yaml"],
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load(name: str) -> dict:
    with (SPECS_DIR / name).open() as f:
        return yaml.safe_load(f)


def simplify_schema(schema) -> dict:
    """
    Replace any schema that references external components or contains
    allOf/oneOf/anyOf/$ref with additionalProperties:true.
    Keep simple leaf schemas (type + optional enum/description/format/default).
    """
    if not isinstance(schema, dict):
        return {"type": "object", "additionalProperties": True}

    # If it has a $ref, replace entirely
    if "$ref" in schema:
        return {"type": "object", "additionalProperties": True}

    # If it has composition keywords, replace entirely
    if any(k in schema for k in ("allOf", "oneOf", "anyOf")):
        return {"type": "object", "additionalProperties": True}

    schema_type = schema.get("type")

    # Simple scalar types: keep as-is
    if schema_type in ("string", "integer", "number", "boolean"):
        # Copy allowed keys only
        simple: dict = {"type": schema_type}
        for k in ("enum", "default", "description", "format", "minimum", "maximum", "x-ms-summary"):
            if k in schema:
                simple[k] = schema[k]
        return simple

    # Arrays: simplify items
    if schema_type == "array":
        items = schema.get("items", {})
        simplified_items = simplify_schema(items)
        result: dict = {"type": "array", "items": simplified_items}
        for k in ("description", "x-ms-summary"):
            if k in schema:
                result[k] = schema[k]
        return result

    # Objects: keep only simple properties, replace complex ones
    if schema_type == "object" or "properties" in schema:
        result = {"type": "object"}
        if "additionalProperties" in schema:
            result["additionalProperties"] = schema["additionalProperties"]
        for k in ("description", "x-ms-summary"):
            if k in schema:
                result[k] = schema[k]

        props = schema.get("properties")
        if props:
            simplified_props = {}
            for prop_name, prop_val in props.items():
                simplified_props[prop_name] = simplify_schema(prop_val)
            result["properties"] = simplified_props

        # Keep required if present
        if "required" in schema:
            result["required"] = schema["required"]

        return result

    # Anything else: generic object
    return {"type": "object", "additionalProperties": True}


def simplify_body_schema(schema) -> dict:
    """For request/response bodies: always use additionalProperties:true."""
    return {"type": "object", "additionalProperties": True}


def simplify_path_item(item: dict, simplify_bodies: bool = True) -> dict:
    """
    Deep-copy a path item and simplify all request/response body schemas.
    Keep parameter schemas (they tend to be simple scalars/enums).
    Strip security overrides per-operation.
    Ensure x-ms-summary on every operation.
    """
    item = copy.deepcopy(item)
    http_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}

    for method, op in item.items():
        if method not in http_methods or not isinstance(op, dict):
            continue

        # Remove per-operation security
        op.pop("security", None)

        # Ensure x-ms-summary from summary if missing
        if "x-ms-summary" not in op and "summary" in op:
            op["x-ms-summary"] = op["summary"]

        # Simplify requestBody
        if simplify_bodies and "requestBody" in op:
            rb = op["requestBody"]
            if isinstance(rb, dict) and "content" in rb:
                for media_type, media_obj in rb["content"].items():
                    if isinstance(media_obj, dict) and "schema" in media_obj:
                        media_obj["schema"] = simplify_body_schema(media_obj["schema"])

        # Simplify responses
        if "responses" in op:
            drop_response_headers(op["responses"])
            for status, resp in op["responses"].items():
                if not isinstance(resp, dict):
                    continue
                if "$ref" in resp:
                    op["responses"][status] = {"description": "Response"}
                    continue
                content = resp.get("content", {})
                for media_type, media_obj in content.items():
                    if isinstance(media_obj, dict) and "schema" in media_obj:
                        s = media_obj["schema"]
                        if isinstance(s, dict) and "$ref" in s:
                            media_obj["schema"] = simplify_body_schema(s)
                        elif media_type != "text/event-stream":
                            media_obj["schema"] = simplify_body_schema(s)

        # Simplify parameters
        params = op.get("parameters", [])
        for param in params:
            if not isinstance(param, dict):
                continue
            if "schema" in param:
                param["schema"] = simplify_schema(param["schema"])
            if "x-ms-summary" not in param and "name" in param:
                # Generate a reasonable summary from the param name
                param["x-ms-summary"] = param["name"].replace("_", " ").replace("-", " ").title()

    # Simplify path-level parameters
    path_params = item.get("parameters", [])
    for param in path_params:
        if isinstance(param, dict) and "schema" in param and "$ref" not in param:
            param["schema"] = simplify_schema(param["schema"])

    return item


SKIP_PARAM_NAMES_LOWER = {
    "x-snowflake-authorization-token-type",
    "x-snowflake-role",
    "x-snowflake-warehouse",
    "x-snowflake-database",
    "x-snowflake-schema",
    "authorization",
    "snowflakeauthorizationtokentype",
}

LEGACY_PARAM_REF = "#/components/parameters/snowflakeAuthorizationTokenType"
CANONICAL_PARAM_REF = "#/components/parameters/SnowflakeAuthorizationTokenType"


def scrub_param_list(params: list) -> list:
    """Remove header params that we own (will be injected as path-level SF params)."""
    result = []
    for p in params:
        if isinstance(p, dict):
            if "$ref" in p:
                # Fix legacy ref
                if p["$ref"] == LEGACY_PARAM_REF:
                    p["$ref"] = CANONICAL_PARAM_REF
                result.append(p)
                continue
            name = p.get("name", "")
            in_ = p.get("in", "")
            if in_ == "header" and name.lower() in SKIP_PARAM_NAMES_LOWER:
                continue
        result.append(p)
    return result


def walk_and_fix_refs(node, valid_params: set[str]):
    """Remove any $ref params that point to missing components."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k == "$ref" and isinstance(v, str):
                if v.startswith("#/components/parameters/"):
                    param_name = v.split("/")[-1]
                    if param_name not in valid_params:
                        # Replace with a placeholder that won't cause ref errors
                        node.clear()
                        node["name"] = param_name
                        node["in"] = "query"
                        node["required"] = False
                        node["schema"] = {"type": "string"}
            else:
                walk_and_fix_refs(v, valid_params)
    elif isinstance(node, list):
        for item in node:
            walk_and_fix_refs(item, valid_params)


def validate_refs(spec: dict) -> list[tuple[str, str]]:
    """Find all unresolved local $refs. Returns list of (path, ref) pairs."""
    missing = []

    def _walk(node, path="$"):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    if not v.startswith("#/"):
                        missing.append((path, v))
                        continue
                    parts = v[2:].split("/")
                    cur = spec
                    ok = True
                    for p in parts:
                        if isinstance(cur, dict) and p in cur:
                            cur = cur[p]
                        else:
                            ok = False
                            break
                    if not ok:
                        missing.append((path, v))
                else:
                    _walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(spec)
    return missing


def check_forbidden(spec: dict) -> dict[str, list[str]]:
    """Find remaining allOf/discriminator in the spec."""
    found_allof = []
    found_disc = []

    def _walk(node, path="$"):
        if isinstance(node, dict):
            if "allOf" in node:
                found_allof.append(path)
            if "discriminator" in node:
                found_disc.append(path)
            for k, v in node.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(spec)
    return {"allOf": found_allof, "discriminator": found_disc}


# ---------------------------------------------------------------------------
# Build one group spec
# ---------------------------------------------------------------------------


def load_common_params() -> dict:
    """Load all parameter definitions from common.yaml for inline resolution."""
    common = load("common.yaml")
    return (common.get("components") or {}).get("parameters") or {}


COMMON_PARAMS: dict = {}  # populated in main()


def resolve_param_ref(ref: str) -> dict | None:
    """If a $ref points to common.yaml params, return the resolved param dict."""
    if "common.yaml#/components/parameters/" in ref:
        param_name = ref.split("/")[-1]
        return COMMON_PARAMS.get(param_name)
    return None


def resolve_path_params(params: list) -> list:
    """Expand any $ref params from common.yaml into inline param objects."""
    result = []
    for p in params:
        if isinstance(p, dict) and "$ref" in p and len(p) == 1:
            resolved = resolve_param_ref(p["$ref"])
            if resolved is not None:
                inline = copy.deepcopy(resolved)
                if "schema" in inline:
                    inline["schema"] = simplify_schema(inline["schema"])
                if "x-ms-summary" not in inline and "name" in inline:
                    inline["x-ms-summary"] = inline["name"].replace("_", " ").replace("-", " ").title()
                result.append(inline)
            # else: unknown ref — drop it
        else:
            result.append(p)
    return result


def drop_response_headers(responses: dict) -> None:
    """Remove headers from all responses (avoids broken $refs to headers components)."""
    for status, resp in (responses or {}).items():
        if isinstance(resp, dict):
            resp.pop("headers", None)


def build_group(
    title: str,
    version: str,
    description: str,
    source_files: list[str],
) -> dict:
    """
    Build a self-contained OpenAPI spec for one group.
    """
    spec: dict = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
            "contact": {
                "name": "Snowflake, Inc.",
                "url": "https://snowflake.com",
                "email": "support@snowflake.com",
            },
        },
        "servers": copy.deepcopy(SERVERS),
        "security": [{"SnowflakeOAuth": ["session:role:DEV_FDH_PROJ_MGMT_RW"]}],
        "tags": [],
        "paths": {},
        "components": {
            "securitySchemes": copy.deepcopy(SECURITY_SCHEMES),
            "parameters": copy.deepcopy(SF_PARAMS),
            "schemas": {},
        },
    }

    seen_tags: set[str] = set()
    seen_op_ids: set[str] = set()

    for src_file in source_files:
        if src_file == "MANUAL":
            # Inject manual paths
            for path, item in MANUAL_PATHS.items():
                path_item = simplify_path_item(item, simplify_bodies=False)
                existing_params = path_item.get("parameters", []) or []
                existing_params = scrub_param_list(existing_params)
                path_item["parameters"] = list(SF_PATH_PARAMS) + existing_params
                spec["paths"][path] = path_item
            spec["tags"].append({"name": "Cortex Agents", "description": "Cortex Agent objects and threads"})
            seen_tags.add("Cortex Agents")
            continue

        src = load(src_file)
        prefix = src_file.replace(".yaml", "").replace("-", "_").replace("cortex_", "").replace("_service", "")

        # Collect tags
        for tag in src.get("tags", []) or []:
            tag_name = tag.get("name")
            if tag_name and tag_name not in seen_tags:
                spec["tags"].append(tag)
                seen_tags.add(tag_name)

        # Merge paths
        for path, item in (src.get("paths") or {}).items():
            path_item = simplify_path_item(item)

            # Resolve and scrub per-item params
            item_params = path_item.get("parameters", []) or []
            item_params = resolve_path_params(item_params)
            item_params = scrub_param_list(item_params)
            path_item["parameters"] = list(SF_PATH_PARAMS) + item_params

            # Prefix operationIds
            for method, op in path_item.items():
                if method in {"parameters", "summary", "description", "servers"}:
                    continue
                if not isinstance(op, dict):
                    continue
                # Resolve and scrub per-op params too
                if "parameters" in op:
                    op["parameters"] = resolve_path_params(op["parameters"])
                    op["parameters"] = scrub_param_list(op["parameters"])
                op_id = op.get("operationId")
                if op_id:
                    prefixed = f"{prefix}_{op_id}"
                    if prefixed in seen_op_ids:
                        prefixed = f"{prefix}_{path.replace('/', '_')}_{op_id}"
                    op["operationId"] = prefixed
                    seen_op_ids.add(prefixed)

            if path not in spec["paths"]:
                spec["paths"][path] = path_item

    # No schemas needed (additionalProperties:true throughout)
    # But validate and fix any stray refs
    valid_params = set(spec["components"]["parameters"].keys())
    walk_and_fix_refs(spec["paths"], valid_params)

    return spec


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global COMMON_PARAMS
    COMMON_PARAMS = load_common_params()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for (out_file, title, version, description, source_files) in SPLIT_GROUPS:
        print(f"\nBuilding {out_file} ...")
        spec = build_group(title, version, description, source_files)

        # Verify
        missing_refs = validate_refs(spec)
        forbidden = check_forbidden(spec)

        path_count = len(spec["paths"])
        schema_count = len(spec["components"].get("schemas", {}))
        param_count = len(spec["components"].get("parameters", {}))

        warnings = []
        if missing_refs:
            warnings.append(f"{len(missing_refs)} unresolved refs")
            for p, r in missing_refs[:5]:
                print(f"    !! unresolved: {p} -> {r}")
        if forbidden["allOf"]:
            warnings.append(f"allOf at: {forbidden['allOf'][:3]}")
        if forbidden["discriminator"]:
            warnings.append(f"discriminator at: {forbidden['discriminator'][:3]}")

        out_path = OUT_DIR / out_file
        with out_path.open("w") as f:
            yaml.safe_dump(spec, f, sort_keys=False, width=120, allow_unicode=True)

        status = "✓" if not warnings else "⚠"
        print(f"  {status} {out_file}: paths={path_count}, schemas={schema_count}, params={param_count}")
        if warnings:
            for w in warnings:
                print(f"    !! {w}")

        results.append({
            "file": out_file,
            "paths": path_count,
            "schemas": schema_count,
            "params": param_count,
            "warnings": warnings,
        })

    print("\n=== Summary ===")
    for r in results:
        warn_str = f"  WARNINGS: {'; '.join(r['warnings'])}" if r["warnings"] else ""
        print(f"  {r['file']}: paths={r['paths']}, schemas={r['schemas']}, params={r['params']}{warn_str}")

    return results


if __name__ == "__main__":
    main()
