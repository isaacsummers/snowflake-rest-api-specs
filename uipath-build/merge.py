#!/usr/bin/env python3
"""
Merge selected Snowflake REST API spec files into a single UiPath-compatible
OpenAPI 3.0.x document.

Design:
- Scoped to Cortex Search and Cortex Analyst only.
- OAuth2 Authorization Code flow via Entra ID external OAuth integration.
  Tenant ID placeholders ({ENTRA_TENANT_ID}) must be substituted before use.
- X-Snowflake-Authorization-Token-Type defaults to OAUTH (not PAT).
- X-Snowflake-* connection headers defined as reusable components/parameters,
  attached at the path-item level (NOT per-operation) so each operation
  inherits them once.
- All cross-file $refs rewritten to local `#/components/...` after components
  are merged in.
- Server URL templated as `https://{account}.snowflakecomputing.com`.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

SPECS_DIR = Path("/home/ubuntu/projects/snowflake-rest-api-specs/specifications")
OUT_PATH = Path("/home/ubuntu/projects/snowflake-rest-api-specs/build/uipath-snowflake-cortex.yaml")  # output; copy to uipath-ready/v1/snowflake-cortex-rest-api-v1.yaml

COMMON_FILES = [
    "common.yaml",
    "common-cortex-analyst.yaml",
]

PATH_FILES = [
    ("cortex-analyst.yaml", "cortexAnalyst"),
    ("cortex-search-service.yaml", "cortexSearch"),
]

# Only keep these paths — trims the UiPath activity list to the essentials.
KEEP_PATHS = {
    "/api/v2/cortex/analyst/message",
    "/api/v2/databases/{database}/schemas/{schema}/cortex-search-services/{service_name}:query",
    "/api/v2/databases/{database}/schemas/{schema}/cortex-search-services/{service_name}:suggest",
}



def load(name: str) -> dict:
    with (SPECS_DIR / name).open() as f:
        return yaml.safe_load(f)


def rewrite_refs(node, file_set: set[str]):
    """Walk YAML tree; rewrite cross-file $refs to local refs.

    `common.yaml#/components/schemas/Foo` -> `#/components/schemas/Foo`
    """
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


def deep_merge_components(target: dict, src: dict, source_label: str):
    """Merge components.{schemas,parameters,responses,headers,...} dicts.

    On collisions: keep first-loaded definition; warn on conflicting bodies.
    """
    for section, defs in src.items():
        if not isinstance(defs, dict):
            target[section] = defs
            continue
        bucket = target.setdefault(section, {})
        for name, body in defs.items():
            if name in bucket and bucket[name] != body:
                print(f"  ! components.{section}.{name}: duplicate from "
                      f"{source_label} differs from earlier; keeping first",
                      file=sys.stderr)
                continue
            bucket[name] = body


def main():
    file_set = set(COMMON_FILES + [name for name, _ in PATH_FILES])

    merged: dict = {
        "openapi": "3.0.0",
        "info": {
            "title": "Snowflake Cortex REST API v1",
            "version": "1.0.0",
            "description": (
                "Snowflake Cortex REST API — packaged for UiPath Integration Service. "
                "v1 covers Cortex Analyst (sendMessage) and Cortex Search (query, suggest). "
                "Future versions will expand to additional Cortex endpoints. "
                "Auth: OAuth 2.0 Authorization Code via Entra ID external OAuth integration "
                "(tenant d73a39db-6eda-495d-8000-7579f56d68b7). "
                "Connection-level fields supply default Snowflake context (account, warehouse, "
                "database, schema, role); per-call parameters allow per-request overrides."
            ),
            "contact": {
                "name": "Snowflake, Inc.",
                "url": "https://snowflake.com",
                "email": "support@snowflake.com",
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
                        "Snowflake-native OAuth 2.0 Authorization Code. "
                        "Auth and token URLs point to your Snowflake account. "
                        "Scope: session:role:<ROLE>. Configure client ID, secret, "
                        "and callback URL in the UiPath Integration Service connection."
                    ),
                    "flows": {
                        "authorizationCode": {
                            "authorizationUrl": (
                                "https://login.microsoftonline.com/d73a39db-6eda-495d-8000-7579f56d68b7/oauth2/v2.0/authorize"
                            ),
                            "tokenUrl": (
                                "https://login.microsoftonline.com/d73a39db-6eda-495d-8000-7579f56d68b7/oauth2/v2.0/token"
                            ),
                            "scopes": {
                                "session:role:DEV_FDH_PROJ_MGMT_RW": "Access Snowflake APIs with DEV_FDH_PROJ_MGMT_RW role"
                            },
                            "x-ms-connection-parameter": {
                                "name": "token",
                                "uiDefinition": {
                                    "displayName": "OAuth Scope",
                                    "description": "Snowflake session scope. Format: session:role:<ROLE>",
                                    "constraints": {
                                        "required": "true",
                                        "allowedValues": [
                                            {
                                                "text": "DEV_FDH_PROJ_MGMT_RW",
                                                "value": "session:role:DEV_FDH_PROJ_MGMT_RW",
                                            }
                                        ],
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
        comps = spec.get("components", {})
        for section, defs in comps.items():
            if section == "securitySchemes":
                continue
            target_section = merged["components"].setdefault(section, {})
            for name, body in defs.items():
                if name in target_section and target_section[name] != body:
                    print(f"  ! components.{section}.{name} collision in "
                          f"{fname}; keeping first", file=sys.stderr)
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
            "description": (
                "Snowflake role to use for the request. Must be granted to "
                "the user. Omit to use the user's default role."
            ),
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
            "description": (
                "Snowflake warehouse to use. Role must have USAGE on it. "
                "Omit to use the user's default warehouse."
            ),
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
            "description": "Default Snowflake database context for the request.",
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
            "description": "Default Snowflake schema context for the request.",
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
        # Trim to only the paths we need
        if "paths" in spec:
            spec["paths"] = {p: v for p, v in spec["paths"].items() if p in KEEP_PATHS}

        for section, defs in (spec.get("components") or {}).items():
            if section == "securitySchemes":
                continue
            target_section = merged["components"].setdefault(section, {})
            if not isinstance(defs, dict):
                continue
            for name, body in defs.items():
                if section == "parameters" and name in sf_param_defs:
                    continue
                if name in target_section and target_section[name] != body:
                    print(f"  ! components.{section}.{name} collision in "
                          f"{fname}; keeping first", file=sys.stderr)
                    continue
                target_section[name] = body

        for tag in spec.get("tags", []) or []:
            if tag.get("name") not in seen_tags:
                merged["tags"].append(tag)
                seen_tags.add(tag.get("name"))

        for path, item in (spec.get("paths") or {}).items():
            stripped_item = copy.deepcopy(item)
            for method, op in list(stripped_item.items()):
                if isinstance(op, dict) and "security" in op:
                    op.pop("security", None)
            if path in merged["paths"]:
                existing = merged["paths"][path]
                for k, v in stripped_item.items():
                    if k in existing:
                        print(f"  ! path {path} method {k} already defined; "
                              f"skipping dup from {fname}", file=sys.stderr)
                        continue
                    existing[k] = v
                continue
            new_item = stripped_item
            existing_params = new_item.get("parameters", []) or []
            new_item["parameters"] = list(sf_path_level_params) + existing_params
            for method, op in list(new_item.items()):
                if method in {"parameters", "summary", "description", "servers"}:
                    continue
                if not isinstance(op, dict):
                    continue
                op_id = op.get("operationId")
                if op_id and op_id in seen_op_ids:
                    op["operationId"] = f"{prefix}_{op_id}"
                if op_id:
                    seen_op_ids.add(op.get("operationId"))
            merged["paths"][path] = new_item

    # --- 4. Final cleanup ---
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
                if out == "__DROP__":
                    continue
                cleaned.append(item)
            node[:] = cleaned
            return node
        return node

    _scrub(merged.get("paths", {}))

    # --- 5. Validate every $ref resolves locally ---
    missing = []

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
        for p, r in missing[:20]:
            print(f"    {p} -> {r}", file=sys.stderr)
        if len(missing) > 20:
            print(f"    ... and {len(missing) - 20} more", file=sys.stderr)

    # --- 6. Emit ---
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        yaml.safe_dump(merged, f, sort_keys=False, width=100)

    print(f"\nWrote {OUT_PATH}  (paths: {len(merged['paths'])}, "
          f"schemas: {len(merged['components'].get('schemas', {}))}, "
          f"parameters: {len(merged['components'].get('parameters', {}))})")


if __name__ == "__main__":
    main()
