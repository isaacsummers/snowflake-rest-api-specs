#!/usr/bin/env python3
"""
Merge selected Snowflake REST API spec files into a single UiPath-compatible
OpenAPI 3.0.x document — v2 (expanded).

Scope:
- Cortex Analyst, Cortex Search, Cortex Inference/complete, Cortex Embed,
  Cortex OpenAI-compat (chat completions), Cortex Anthropic-compat (messages),
  SQL API (statements).
- All paths from the above files are included (no KEEP_PATHS filter).
- operationIds are always prefixed with the file-group prefix to avoid collisions.
- sqlapi.yaml uses a lowercase `snowflakeAuthorizationTokenType` param ref;
  _scrub rewrites it to the canonical PascalCase name.
- OAuth2 Authorization Code via Entra ID; connection parameters for Snowflake context.
"""
from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

import yaml

SPECS_DIR = Path("/home/ubuntu/projects/snowflake-rest-api-specs/specifications")
OUT_PATH = Path(
    "/home/ubuntu/projects/snowflake-rest-api-specs/uipath-ready/v2/snowflake-rest-api-v2.yaml"
)
COPY_PATH = Path(
    "/home/ubuntu/projects/snowflake-rest-api-specs/build/uipath-snowflake-cortex-v2.yaml"
)

# common-cortex-agent.yaml and common-cortex-tool.yaml have no cross-file refs
# in the target path files (verified by grep), so they are not included.
COMMON_FILES = [
    "common.yaml",
    "common-cortex-analyst.yaml",
]

PATH_FILES = [
    ("cortex-analyst.yaml",           "cortexAnalyst"),
    ("cortex-search-service.yaml",    "cortexSearch"),
    ("cortex-inference.yaml",         "cortexInference"),
    ("cortex-embed.yaml",             "cortexEmbed"),
    ("cortex-generic-openai.yaml",    "cortexOpenAI"),
    ("cortex-generic-anthropic.yaml", "cortexAnthropic"),
    ("sqlapi.yaml",                   "sqlApi"),
]

# None = keep all paths from all PATH_FILES (no filtering)
KEEP_PATHS = None


def load(name: str) -> dict:
    with (SPECS_DIR / name).open() as f:
        return yaml.safe_load(f)


def rewrite_refs(node, file_set: set[str]):
    """Rewrite cross-file $refs to local #/components/... refs."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k == "$ref" and isinstance(v, str):
                stripped = v[2:] if v.startswith("./") else v
                for fname in file_set:
                    prefix = f"{fname}#"
                    if stripped.startswith(prefix):
                        node[k] = "#" + stripped[len(prefix):]
                        break
            else:
                rewrite_refs(v, file_set)
    elif isinstance(node, list):
        for item in node:
            rewrite_refs(item, file_set)


def main():
    file_set = set(COMMON_FILES + [name for name, _ in PATH_FILES])

    merged: dict = {
        "openapi": "3.0.0",
        "info": {
            "title": "Snowflake REST API v2",
            "version": "2.0.0",
            "description": (
                "Snowflake REST API — packaged for UiPath Integration Service. "
                "v2 covers Cortex Analyst (sendMessage), Cortex Search (query, suggest), "
                "Cortex Inference (complete), Cortex Embed (embed), "
                "Cortex OpenAI-compat (chat/completions), "
                "Cortex Anthropic-compat (messages), SQL API (statements), "
                "and Cortex Agents (threads, agent objects, agent run). "
                "Auth: Snowflake-native OAuth 2.0 Authorization Code. "
                "Connection-level fields supply default Snowflake context (account, warehouse, "
                "database, schema, role); per-call parameters allow per-request overrides."
            ),
            "contact": {
                "name": "Snowflake, Inc.",
                "url": "https://snowflake.com",
                "email": "support@snowflake.com",
            },
            "license": {
                "name": "Snowflake Developer Policy",
                "url": "https://www.snowflake.com/legal/developer-policy/",
            },
        },
        "servers": [
            {
                "url": "https://{account}.snowflakecomputing.com",
                "description": "Snowflake account endpoint",
                "variables": {
                    "account": {
                        "default": "MDTPLC-AWSUSE1P1",
                        "description": (
                            "Snowflake account identifier "
                            "(e.g. MDTPLC-AWSUSE1P1). No "
                            "'.snowflakecomputing.com' suffix."
                        ),
                        "x-ms-connection-parameter": {
                            "name": "account",
                            "uiDefinition": {
                                "displayName": "Snowflake Account",
                                "description": "Your Snowflake account identifier (e.g. MDTPLC-AWSUSE1P1)",
                                "tooltip": "Find under Admin > Accounts or run SELECT CURRENT_ACCOUNT() in Snowflake",
                                "constraints": {
                                    "required": "true",
                                },
                            },
                        },
                    }
                },
            }
        ],
        "security": [
            {
                "SnowflakeOAuth": [
                    "session:role:DEV_FDH_PROJ_MGMT_RW"
                ]
            }
        ],
        "tags": [],
        "paths": {},
        "components": {
            "securitySchemes": {
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
                                    "constraints": {
                                        "required": "true",
                                    },
                                },
                            },
                        }
                    },
                }
            },
            "parameters": {},
            "schemas": {},
            "responses": {},
            "headers": {},
            "requestBodies": {},
            "examples": {},
        },
    }

    # --- 1. Load shared component files ---
    for fname in COMMON_FILES:
        spec = load(fname)
        rewrite_refs(spec, file_set)
        for section, defs in (spec.get("components") or {}).items():
            if section == "securitySchemes":
                continue
            target_section = merged["components"].setdefault(section, {})
            if not isinstance(defs, dict):
                continue
            for name, body in defs.items():
                if name in target_section and target_section[name] != body:
                    print(
                        f"  ! components.{section}.{name} collision in "
                        f"{fname}; keeping first",
                        file=sys.stderr,
                    )
                    continue
                target_section[name] = body

    # --- 2. Add UiPath connection-level Snowflake context parameters ---
    sf_param_defs = {
        "SnowflakeAuthorizationTokenType": {
            "name": "X-Snowflake-Authorization-Token-Type",
            "in": "header",
            "required": True,
            "description": (
                "Snowflake authorization token type. For OAuth use OAUTH; "
                "for PAT use PROGRAMMATIC_ACCESS_TOKEN. Must match the token "
                "in Authorization or Snowflake returns 401."
            ),
            "x-ms-visibility": "advanced",
            "schema": {
                "type": "string",
                "enum": ["OAUTH", "PROGRAMMATIC_ACCESS_TOKEN", "KEYPAIR_JWT"],
                "default": "OAUTH",
                "x-ms-summary": "Token Type",
            },
        },
        "SnowflakeRole": {
            "name": "X-Snowflake-Role",
            "in": "header",
            "required": False,
            "description": (
                "Snowflake role to use for the request. Must be granted to "
                "the user. Omit to use the user's default role."
            ),
            "x-ms-visibility": "advanced",
            "schema": {"type": "string", "default": "DEV_FDH_PROJ_MGMT_RW", "x-ms-summary": "Role"},
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
            "description": (
                "Snowflake warehouse to use. Role must have USAGE on it. "
                "Omit to use the user's default warehouse."
            ),
            "x-ms-visibility": "advanced",
            "schema": {"type": "string", "default": "AGENT_WH", "x-ms-summary": "Warehouse"},
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
            "description": "Default Snowflake database context for the request.",
            "x-ms-visibility": "advanced",
            "schema": {"type": "string", "default": "DEV_FDH_DB", "x-ms-summary": "Default Database"},
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
            "description": "Default Snowflake schema context for the request.",
            "x-ms-visibility": "advanced",
            "schema": {"type": "string", "default": "PROJ_MGMT", "x-ms-summary": "Default Schema"},
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

    # Remove any legacy lowercase variants loaded from common files
    legacy_keys = [
        k for k in list(merged["components"]["parameters"])
        if k.lower() in {
            "snowflakeauthorizationtokentype",
            "x-snowflake-authorization-token-type",
        }
    ]
    for k in legacy_keys:
        merged["components"]["parameters"].pop(k, None)

    merged["components"]["parameters"].update(sf_param_defs)

    sf_path_level_params = [
        {"$ref": f"#/components/parameters/{name}"}
        for name in [
            "SnowflakeAuthorizationTokenType",
            "SnowflakeRole",
            "SnowflakeWarehouse",
            "SnowflakeDatabase",
            "SnowflakeSchema",
        ]
    ]

    # --- 3. Load path-bearing specs ---
    seen_tags: set[str] = set()
    seen_op_ids: set[str] = set()

    for fname, prefix in PATH_FILES:
        spec = load(fname)
        rewrite_refs(spec, file_set)

        # Filter paths if KEEP_PATHS is set
        if KEEP_PATHS is not None and "paths" in spec:
            spec["paths"] = {
                p: v for p, v in spec["paths"].items() if p in KEEP_PATHS
            }

        # Merge components (skip securitySchemes)
        for section, defs in (spec.get("components") or {}).items():
            if section == "securitySchemes":
                continue
            target_section = merged["components"].setdefault(section, {})
            if not isinstance(defs, dict):
                continue
            for name, body in defs.items():
                # Skip: we own all SF connection params
                if section == "parameters" and name in sf_param_defs:
                    continue
                # Also skip the lowercase sqlapi variant — handled by _scrub
                if section == "parameters" and name.lower() in {
                    "snowflakeauthorizationtokentype",
                    "x-snowflake-authorization-token-type",
                }:
                    continue
                if name in target_section and target_section[name] != body:
                    print(
                        f"  ! components.{section}.{name} collision in "
                        f"{fname}; keeping first",
                        file=sys.stderr,
                    )
                    continue
                target_section[name] = body

        # Merge tags
        for tag in spec.get("tags", []) or []:
            if tag.get("name") not in seen_tags:
                merged["tags"].append(tag)
                seen_tags.add(tag.get("name"))

        # Merge paths
        for path, item in (spec.get("paths") or {}).items():
            stripped_item = copy.deepcopy(item)

            # Strip per-operation security overrides
            for method, op in list(stripped_item.items()):
                if isinstance(op, dict) and "security" in op:
                    op.pop("security", None)

            if path in merged["paths"]:
                existing = merged["paths"][path]
                for k, v in stripped_item.items():
                    if k in existing:
                        print(
                            f"  ! path {path} method {k} already defined; "
                            f"skipping dup from {fname}",
                            file=sys.stderr,
                        )
                        continue
                    existing[k] = v
                continue

            new_item = stripped_item
            existing_params = new_item.get("parameters", []) or []
            new_item["parameters"] = list(sf_path_level_params) + existing_params

            # Always prefix operationIds with the file-group prefix
            for method, op in list(new_item.items()):
                if method in {"parameters", "summary", "description", "servers"}:
                    continue
                if not isinstance(op, dict):
                    continue
                op_id = op.get("operationId")
                if op_id:
                    prefixed = f"{prefix}_{op_id}"
                    if prefixed in seen_op_ids:
                        # Shouldn't happen but make it unique
                        prefixed = f"{prefix}_{fname.replace('.yaml','')}_{op_id}"
                    op["operationId"] = prefixed
                    seen_op_ids.add(prefixed)

            merged["paths"][path] = new_item

    # --- 3.5. Inject hand-built Cortex Agents paths ---
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
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": True,
                                }
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
                                        "items": {"type": "object", "additionalProperties": True},
                                        "description": "Tools available to the agent",
                                    },
                                    "tool_resources": {
                                        "type": "object",
                                        "additionalProperties": True,
                                        "description": "Resources for tools",
                                    },
                                    "tool_choice": {
                                        "type": "object",
                                        "additionalProperties": True,
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
                            "text/event-stream": {
                                "schema": {"type": "string"}
                            },
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": True,
                                }
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
                    {
                        "name": "database",
                        "in": "path",
                        "required": True,
                        "x-ms-summary": "Database",
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "schema",
                        "in": "path",
                        "required": True,
                        "x-ms-summary": "Schema",
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "createMode",
                        "in": "query",
                        "required": False,
                        "x-ms-summary": "Create Mode",
                        "schema": {
                            "type": "string",
                            "enum": ["errorIfExists", "orReplace", "ifNotExists"],
                        },
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
                                    "name": {"type": "string"},
                                    "comment": {"type": "string"},
                                    "profile": {"type": "object", "additionalProperties": True},
                                    "models": {"type": "object", "additionalProperties": True},
                                    "instructions": {"type": "object", "additionalProperties": True},
                                    "orchestration": {"type": "object", "additionalProperties": True},
                                    "tools": {
                                        "type": "array",
                                        "items": {"type": "object", "additionalProperties": True},
                                    },
                                    "tool_resources": {"type": "object", "additionalProperties": True},
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
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"}
                                    },
                                }
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
                                    "orig_request_id": {
                                        "type": "string",
                                        "description": "Request ID for the message being rated",
                                        "x-ms-summary": "Original Request ID",
                                    },
                                    "positive": {
                                        "type": "boolean",
                                        "description": "True for positive feedback, false for negative",
                                        "x-ms-summary": "Positive",
                                    },
                                    "feedback_message": {
                                        "type": "string",
                                        "description": "Detailed feedback text",
                                        "x-ms-summary": "Feedback Message",
                                    },
                                    "categories": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Feedback categories",
                                        "x-ms-summary": "Categories",
                                    },
                                    "thread_id": {
                                        "type": "integer",
                                        "description": "Thread ID",
                                        "x-ms-summary": "Thread ID",
                                    },
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
                                "schema": {
                                    "type": "object",
                                    "properties": {"status": {"type": "string", "description": "Feedback submitted successfully"}},
                                }
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
                                    "messages": {
                                        "type": "array",
                                        "items": {"type": "object", "additionalProperties": True},
                                    },
                                    "stream": {"type": "boolean", "default": True, "x-ms-summary": "Stream Response"},
                                    "thread_id": {"type": "integer", "x-ms-summary": "Thread ID"},
                                    "parent_message_id": {"type": "integer", "x-ms-summary": "Parent Message ID"},
                                    "tool_choice": {"type": "object", "additionalProperties": True},
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

    # Standard error responses to add to every MANUAL_PATHS operation
    _STD_ERR_RESPONSES = {
        "400": {"$ref": "#/components/responses/400BadRequest"},
        "401": {"$ref": "#/components/responses/401Unauthorized"},
        "403": {"$ref": "#/components/responses/403Forbidden"},
        "500": {"$ref": "#/components/responses/500InternalServerError"},
        "503": {"$ref": "#/components/responses/503ServiceUnavailable"},
    }

    for path, item in MANUAL_PATHS.items():
        path_item = copy.deepcopy(item)
        existing_params = path_item.get("parameters", []) or []
        path_item["parameters"] = list(sf_path_level_params) + existing_params
        # Inject standard error responses into every operation
        for method, op in path_item.items():
            if isinstance(op, dict) and "responses" in op:
                for code, ref in _STD_ERR_RESPONSES.items():
                    op["responses"].setdefault(code, ref)
        if path in merged["paths"]:
            print(f"  ! MANUAL_PATHS: {path} already in merged paths; skipping", file=sys.stderr)
        else:
            merged["paths"][path] = path_item

    # --- 4. Final cleanup (_scrub) ---
    # Rewrite legacy lowercase sqlapi ref and drop duplicate header params
    legacy_ref_targets = {
        "#/components/parameters/snowflakeAuthorizationTokenType":
            "#/components/parameters/SnowflakeAuthorizationTokenType",
    }

    def _scrub(node):
        if isinstance(node, dict):
            name = node.get("name")
            in_ = node.get("in")
            if (
                isinstance(name, str)
                and in_ == "header"
                and (
                    name.lower() == "authorization"
                    or name in {
                        "X-Snowflake-Role",
                        "X-Snowflake-Warehouse",
                        "X-Snowflake-Database",
                        "X-Snowflake-Schema",
                    }
                )
            ):
                return "__DROP__"
            for k, v in list(node.items()):
                if k == "$ref" and isinstance(v, str) and v in legacy_ref_targets:
                    node[k] = legacy_ref_targets[v]
                else:
                    out = _scrub(v)
                    if out == "__DROP__":
                        node.pop(k, None)
            return node
        if isinstance(node, list):
            cleaned = []
            for item in node:
                out = _scrub(item)
                if out != "__DROP__":
                    cleaned.append(item)
            node[:] = cleaned
            return node
        return node

    _scrub(merged.get("paths", {}))

    # --- 4c. Deduplicate path-level parameters (by $ref equality) ---
    for path_item in merged["paths"].values():
        if "parameters" in path_item and isinstance(path_item["parameters"], list):
            seen_params = []
            seen_refs = set()
            for p in path_item["parameters"]:
                if isinstance(p, dict) and "$ref" in p:
                    if p["$ref"] not in seen_refs:
                        seen_refs.add(p["$ref"])
                        seen_params.append(p)
                else:
                    seen_params.append(p)
            path_item["parameters"] = seen_params

    # --- 4b. Flatten allOf / strip discriminators ---

    schemas = merged["components"].get("schemas", {})

    def resolve_ref(ref: str) -> dict | None:
        """Resolve a local #/components/schemas/... ref to its schema dict."""
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        cur = merged
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return None
        return cur if isinstance(cur, dict) else None

    def flatten_inline_allof(schema: dict) -> dict:
        """
        Collapse inline allOf that contains only a single $ref and nothing else
        into a bare $ref.  E.g. {allOf: [{$ref: X}]} -> {$ref: X}
        """
        if isinstance(schema, dict):
            # Recurse into properties first
            for prop_name, prop_val in list(schema.get("properties", {}).items()):
                schema["properties"][prop_name] = flatten_inline_allof(prop_val)
            # Recurse into items
            if "items" in schema:
                schema["items"] = flatten_inline_allof(schema["items"])
            # Collapse single-ref allOf at this level
            if (
                "allOf" in schema
                and len(schema) == 1  # allOf is the only key
                and len(schema["allOf"]) == 1
                and isinstance(schema["allOf"][0], dict)
                and "$ref" in schema["allOf"][0]
                and len(schema["allOf"][0]) == 1
            ):
                return {"$ref": schema["allOf"][0]["$ref"]}
            # Collapse single-ref allOf alongside other non-composition keys
            if "allOf" in schema:
                all_of = schema["allOf"]
                if (
                    len(all_of) == 1
                    and isinstance(all_of[0], dict)
                    and "$ref" in all_of[0]
                    and len(all_of[0]) == 1
                    and not any(k in schema for k in ("oneOf", "anyOf", "properties", "required", "type"))
                ):
                    ref_val = all_of[0]["$ref"]
                    schema.pop("allOf")
                    schema["$ref"] = ref_val
        return schema

    def flatten_schema_allof(name: str, schema: dict, visited: set | None = None) -> dict:
        """
        Fully flatten a top-level schema's allOf into its own properties/required.
        Recursively flattens parent schemas first.
        """
        if visited is None:
            visited = set()
        if name in visited:
            return schema
        visited.add(name)

        if "allOf" not in schema:
            return schema

        # Don't flatten if oneOf/anyOf also present at top level (complex composition)
        if "oneOf" in schema or "anyOf" in schema:
            return schema

        all_of = schema.pop("allOf")
        merged_props: dict = {}
        merged_required: list = []

        for entry in all_of:
            if not isinstance(entry, dict):
                continue
            if "$ref" in entry and len(entry) == 1:
                # Resolve and flatten the parent first
                ref = entry["$ref"]
                parent_schema = resolve_ref(ref)
                if parent_schema is not None:
                    parent_name = ref.split("/")[-1]
                    flatten_schema_allof(parent_name, parent_schema, visited)
                    for p, v in (parent_schema.get("properties") or {}).items():
                        if p not in merged_props:
                            merged_props[p] = v
                    for r in (parent_schema.get("required") or []):
                        if r not in merged_required:
                            merged_required.append(r)
            elif isinstance(entry, dict):
                # Inline object with properties etc.
                for p, v in (entry.get("properties") or {}).items():
                    merged_props[p] = v  # child wins
                for r in (entry.get("required") or []):
                    if r not in merged_required:
                        merged_required.append(r)
                # Copy other keys like type, description at this level
                for k, v in entry.items():
                    if k not in ("properties", "required") and k not in schema:
                        schema[k] = v

        # Merge gathered props/required into the schema
        if merged_props:
            existing_props = schema.get("properties") or {}
            # Child's own properties win
            final_props = {**merged_props, **existing_props}
            schema["properties"] = final_props
        if merged_required:
            existing_req = schema.get("required") or []
            final_req = list(existing_req)  # child's own required first
            for r in merged_required:
                if r not in final_req:
                    final_req.append(r)
            schema["required"] = final_req

        # Set type=object if no type and we now have properties
        if "type" not in schema and schema.get("properties"):
            schema["type"] = "object"

        return schema

    # Iterative pass (max 5 rounds) until no allOf remains at top level
    for _round in range(5):
        changed = False
        for schema_name, schema_body in list(schemas.items()):
            if isinstance(schema_body, dict) and "allOf" in schema_body:
                if "oneOf" not in schema_body and "anyOf" not in schema_body:
                    flatten_schema_allof(schema_name, schema_body)
                    changed = True
        if not changed:
            break

    # Flatten inline single-ref allOf inside all property definitions
    for schema_name, schema_body in list(schemas.items()):
        if isinstance(schema_body, dict):
            flatten_inline_allof(schema_body)

    # Strip discriminator from all schemas
    def _strip_discriminator(node):
        if isinstance(node, dict):
            node.pop("discriminator", None)
            for v in node.values():
                _strip_discriminator(v)
        elif isinstance(node, list):
            for item in node:
                _strip_discriminator(item)

    _strip_discriminator(merged["components"].get("schemas", {}))
    _strip_discriminator(merged.get("paths", {}))

    # Report
    still_allof = [
        n for n, s in schemas.items()
        if isinstance(s, dict) and "allOf" in s and "oneOf" not in s and "anyOf" not in s
    ]
    if still_allof:
        print(f"  ! allOf still present in: {still_allof}", file=sys.stderr)
    else:
        print("  ✓ allOf flattened (no unflattenable allOf remains).", file=sys.stderr)

    # --- 5. Validate every $ref resolves locally ---
    missing: list[tuple[str, str]] = []

    def _walk_refs(node, path="$"):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    if not v.startswith("#/"):
                        missing.append((path, v))
                        continue
                    parts = v[2:].split("/")
                    cur = merged
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
                    _walk_refs(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk_refs(item, f"{path}[{i}]")

    _walk_refs(merged)
    if missing:
        print(f"\n  ! {len(missing)} unresolved refs:", file=sys.stderr)
        for p, r in missing[:30]:
            print(f"    {p} -> {r}", file=sys.stderr)
        if len(missing) > 30:
            print(f"    ... and {len(missing) - 30} more", file=sys.stderr)
    else:
        print("  ✓ All $refs resolved.", file=sys.stderr)

    # --- 5b. Post-process: inject missing summaries for operations that lack them ---
    MISSING_SUMMARIES = {
        "cortexAnalyst_sendFeedback": "Send Analyst Feedback",
        "cortexSearch_sendFeedback": "Send Search Feedback",
    }
    for path_item in merged["paths"].values():
        for method, op in path_item.items():
            if not isinstance(op, dict):
                continue
            op_id = op.get("operationId")
            if op_id in MISSING_SUMMARIES and "summary" not in op:
                op["summary"] = MISSING_SUMMARIES[op_id]

    # --- 5c. Post-process: strip bindings example from sqlapi statements path ---
    statements_path = "/api/v2/statements"
    if statements_path in merged["paths"]:
        try:
            bindings_prop = (
                merged["paths"][statements_path]
                ["post"]["requestBody"]["content"]["application/json"]
                ["schema"]["properties"]["bindings"]
            )
            bindings_prop.pop("example", None)
        except (KeyError, TypeError):
            pass
        # Also strip from the content-level example
        try:
            content = (
                merged["paths"][statements_path]
                ["post"]["requestBody"]["content"]["application/json"]
            )
            if "example" in content and "bindings" in content["example"]:
                content["example"].pop("bindings", None)
        except (KeyError, TypeError):
            pass

    # --- 5d. Post-process: remove unused components ---
    STRIP_UNUSED_COMPONENTS: dict[str, list[str]] = {
        "schemas": [
            "StreamingError",
            "AnthropicOutput",
            "StreamingOpenAIOutput",
            "StreamingAnthropicOutput",
            "NonStreamingCompleteResponse",
        ],
        "responses": [
            "201SuccessCreatedResponse",
        ],
        "parameters": [
            "application",
        ],
    }
    for section, names in STRIP_UNUSED_COMPONENTS.items():
        target = merged["components"].get(section, {})
        for name in names:
            removed = target.pop(name, None)
            if removed is not None:
                print(f"  ✓ Stripped unused component {section}/{name}", file=sys.stderr)

    # --- 6. Emit ---
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        yaml.safe_dump(merged, f, sort_keys=False, width=100)

    COPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_PATH, COPY_PATH)

    # --- 7. swagger-cli validation ---
    import subprocess as _subprocess
    _result = _subprocess.run(
        ["swagger-cli", "validate", str(OUT_PATH)],
        capture_output=True, text=True
    )
    if _result.returncode != 0:
        print(
            f"\n⚠ swagger-cli validation FAILED:\n{_result.stdout}\n{_result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(f"✓ swagger-cli: {OUT_PATH.name} is valid")

    path_count = len(merged["paths"])
    schema_count = len(merged["components"].get("schemas", {}))
    param_count = len(merged["components"].get("parameters", {}))

    print(
        f"\nWrote {OUT_PATH}"
        f"\nCopied to {COPY_PATH}"
        f"\n  paths: {path_count}"
        f"\n  schemas: {schema_count}"
        f"\n  parameters: {param_count}"
    )


if __name__ == "__main__":
    main()
