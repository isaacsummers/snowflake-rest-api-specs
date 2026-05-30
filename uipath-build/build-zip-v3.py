#!/usr/bin/env python3
"""
Build UiPath connector zip for Snowflake REST API v3.
Starts from v2-fixed zip as base, applies:
  1. Config field improvements (descriptions, hints)
  2. Standard-resource fields populated from spec schema
  3. Parameter displayName improvements
Output: uipath-ready/v2/snowflake-rest-api-v2-connector-v3.zip
"""

import copy
import json
import zipfile
from pathlib import Path

BASE_ZIP = Path("/mnt/windows/Downloads/design-medtronicplc-snowflakerestapi-v2-fixed.zip")
OUT_PATH = Path(__file__).parent.parent / "uipath-ready/v2/snowflake-rest-api-v2-connector-v3.zip"
COPY_PATH = Path(__file__).parent.parent / "downloaded/snowflake-rest-api-v2-connector-v3.zip"

CONNECTOR_KEY = "design-medtronicplc-snowflakerestapi"
BASE_PREFIX = f"{CONNECTOR_KEY}/app/element/"

# ---------------------------------------------------------------------------
# Field builder helpers
# ---------------------------------------------------------------------------

def _field(name, display_name, native_type, fmt, description, sample, method="POST"):
    return {
        "method": {method: {"name": method}},
        "displayName": display_name,
        "nativeType": native_type,
        "custom": "no",
        "name": name,
        "format": fmt,
        "description": description,
        "type": native_type,
        "sampleValue": sample,
    }


def str_field(name, display_name, description, method="POST"):
    return _field(name, display_name, "string", "string", description, "", method)


def num_field(name, display_name, description, method="POST"):
    return _field(name, display_name, "number", "double", description, 0, method)


def bool_field(name, display_name, description, method="POST"):
    return _field(name, display_name, "boolean", "boolean", description, True, method)


def obj_field(name, display_name, description, method="POST"):
    return _field(name, display_name, "object", "object", description, {}, method)


def arr_field(name, display_name, description, method="POST"):
    return _field(name, display_name, "array", "array", description, [], method)


# ---------------------------------------------------------------------------
# Field sets per standard resource
# ---------------------------------------------------------------------------

FIELDS_BY_RESOURCE = {
    "CortexAnalyst_sendMessage": {
        "messages": arr_field("messages", "Messages",
            "Conversation messages. Each message has 'role' (user|analyst) and 'content' array."),
        "semantic_model_file": str_field("semantic_model_file", "Semantic Model File",
            "Stage path to semantic model YAML, e.g. @db.schema.stage/path/file.yaml"),
        "semantic_model": str_field("semantic_model", "Semantic Model (inline)",
            "Inline YAML string for the semantic model."),
        "stream": bool_field("stream", "Stream Response",
            "Whether to stream the response (true) or return full JSON (false)."),
        "operation": str_field("operation", "Operation",
            "Response format: 'sql_generation' (default) or 'answer_generation'."),
        "warehouse": str_field("warehouse", "Warehouse",
            "Warehouse for result-set handling when operation=answer_generation."),
    },
    "AgentRun": {
        "messages": arr_field("messages", "Messages",
            "Conversation messages to send to the agent."),
        "stream": bool_field("stream", "Stream Response",
            "Stream the response via SSE (default: true)."),
        "thread_id": num_field("thread_id", "Thread ID",
            "Optional thread ID for conversation continuity."),
        "parent_message_id": num_field("parent_message_id", "Parent Message ID",
            "Optional parent message ID."),
        "tools": arr_field("tools", "Tools",
            "Tools available to the agent."),
        "tool_resources": obj_field("tool_resources", "Tool Resources",
            "Resources for agent tools."),
        "tool_choice": obj_field("tool_choice", "Tool Choice",
            "Tool selection control."),
    },
    "AgentRunWithObject": {
        "messages": arr_field("messages", "Messages",
            "Conversation messages to send to the named agent object."),
        "stream": bool_field("stream", "Stream Response",
            "Stream the response via SSE (default: true)."),
        "thread_id": num_field("thread_id", "Thread ID",
            "Optional thread ID for conversation continuity."),
        "parent_message_id": num_field("parent_message_id", "Parent Message ID",
            "Optional parent message ID."),
        "tools": arr_field("tools", "Tools",
            "Tool overrides for this run."),
        "tool_resources": obj_field("tool_resources", "Tool Resources",
            "Resources for agent tools."),
        "tool_choice": obj_field("tool_choice", "Tool Choice",
            "Tool selection control."),
    },
    "SqlApi_SubmitStatement": {
        "statement": str_field("statement", "SQL Statement",
            "SQL statement to execute. DML, DDL, and queries supported."),
        "timeout": num_field("timeout", "Timeout (seconds)",
            "Execution timeout in seconds. 0 = maximum (604800). Omit for default."),
        "database": str_field("database", "Database",
            "Database context for statement execution (case-sensitive)."),
        "schema": str_field("schema", "Schema",
            "Schema context for statement execution (case-sensitive)."),
        "warehouse": str_field("warehouse", "Warehouse",
            "Warehouse to use for statement execution (case-sensitive)."),
        "role": str_field("role", "Role",
            "Role to use for statement execution (case-sensitive)."),
        "parameters": obj_field("parameters", "Session Parameters",
            "Session parameters to set before executing (e.g. timezone, query_tag)."),
        "bindings": obj_field("bindings", "Bind Variables",
            "Values for bind variables in the SQL statement (? or :name placeholders)."),
    },
    "CortexInference_cortexLLMInferenceComplete": {
        "model": str_field("model", "Model",
            "Model name, e.g. 'claude-3-5-sonnet', 'mistral-large2', 'llama3.1-70b'."),
        "messages": arr_field("messages", "Messages",
            "Conversation messages. Each has 'role' and 'content'."),
        "stream": bool_field("stream", "Stream Response",
            "Stream the response (reserved; set false for standard usage)."),
        "max_tokens": num_field("max_tokens", "Max Tokens",
            "Maximum number of output tokens to generate."),
        "temperature": num_field("temperature", "Temperature",
            "Randomness control: 0 = deterministic, higher = more creative."),
        "top_p": num_field("top_p", "Top P",
            "Nucleus sampling threshold. Typical values: 0.9–1.0."),
    },
    "CortexOpenAI_cortexGenericOpenAIChatCompletions": {
        "model": str_field("model", "Model",
            "Model name for OpenAI-compatible chat completions."),
        "messages": arr_field("messages", "Messages",
            "Array of chat messages with 'role' and 'content' fields."),
        "stream": bool_field("stream", "Stream Response",
            "Stream the response via SSE."),
        "max_tokens": num_field("max_tokens", "Max Tokens",
            "Maximum tokens in the completion."),
        "temperature": num_field("temperature", "Temperature",
            "Sampling temperature. 0 = deterministic."),
    },
    "CortexAnthropic_cortexGenericAnthropicMessages": {
        "model": str_field("model", "Model",
            "Model name for Anthropic-compatible Messages API."),
        "messages": arr_field("messages", "Messages",
            "Array of messages with 'role' and 'content' fields."),
        "max_tokens": num_field("max_tokens", "Max Tokens",
            "Maximum tokens to generate (required by Anthropic API)."),
        "stream": bool_field("stream", "Stream Response",
            "Stream the response via SSE."),
        "system": str_field("system", "System Prompt",
            "System prompt string or array of content blocks."),
    },
    "CortexEmbed_embed": {
        "model": str_field("model", "Model",
            "Embedding model name, e.g. 'snowflake-arctic-embed-m-v1.5'."),
        "input": arr_field("input", "Input Texts",
            "Array of strings to embed. Replaces the 'text' field in newer API versions."),
    },
    "CreateThread": {
        "origin_application": str_field("origin_application", "Origin Application",
            "App name that created the thread (max 16 bytes)."),
    },
    "CreateAgent": {
        "name": str_field("name", "Agent Name",
            "Name of the Cortex Agent object to create."),
        "comment": str_field("comment", "Comment",
            "Optional description or comment for the agent."),
        "profile": obj_field("profile", "Profile",
            "Agent profile configuration object."),
        "models": obj_field("models", "Models",
            "Model configuration for the agent."),
        "instructions": obj_field("instructions", "Instructions",
            "Instructions that define agent behavior."),
        "tools": arr_field("tools", "Tools",
            "Tools available to the agent."),
        "tool_resources": obj_field("tool_resources", "Tool Resources",
            "Resources for agent tools."),
    },
    "CortexSearch_queryCortexSearchService": {
        "query": str_field("query", "Query",
            "Unstructured text query for semantic search."),
        "columns": arr_field("columns", "Columns",
            "List of column names to include in the results."),
        "filter": obj_field("filter", "Filter",
            "Filter expression to narrow search results."),
        "limit": num_field("limit", "Limit",
            "Maximum number of results to return."),
    },
}

# ---------------------------------------------------------------------------
# Config field updates
# ---------------------------------------------------------------------------

CONFIG_UPDATES = {
    "orgname-accountname": {
        "name": "Snowflake Account Identifier",
        "description": "Your Snowflake account identifier in orgname-accountname format (e.g. myorg-myaccount). Find it under Admin > Accounts in Snowsight.",
        "hint": "e.g. myorg-myaccount",
    },
    "oauth.api.key": {
        "name": "Client ID",
        "description": "The Client ID from your Snowflake OAuth integration security integration.",
        "hint": "Your Snowflake OAuth Client ID",
    },
    "oauth.api.secret": {
        "name": "Client Secret",
        "description": "The Client Secret from your Snowflake OAuth security integration.",
    },
    "oauth.scope": {
        "name": "Scope",
        "description": "Snowflake session scope controlling which role to use. Must match a role granted to the OAuth user.",
        "hint": "session:role:MY_ROLE_NAME",
    },
}

# Parameter displayName improvements
PARAM_DISPLAY_NAMES = {
    "database": "Database",
    "schema": "Schema",
    "service_name": "Search Service Name",
    "statementHandle": "Statement Handle",
    "id": "Thread ID",
}

# For name param in agent paths, we want "Agent Name"
AGENT_NAME_PATHS = {"/agents/"}


def apply_param_display_names(resources):
    for res in resources:
        params = res.get("parameters", [])
        for param in params:
            vname = param.get("vendorName", "")
            path = res.get("path", "")
            if vname in PARAM_DISPLAY_NAMES:
                # Special case: 'name' in agent paths
                if vname == "name":
                    continue  # handled below
                param["displayName"] = PARAM_DISPLAY_NAMES[vname]
                param["description"] = PARAM_DISPLAY_NAMES[vname]
            if vname == "name":
                if "/agents/" in path or path.endswith("/agents"):
                    param["displayName"] = "Agent Name"
                    param["description"] = "Agent Name"
                elif "/cortex-search-services/" in path:
                    param["displayName"] = "Search Service Name"
                    param["description"] = "Search Service Name"


def apply_config_updates(configuration):
    for cfg in configuration:
        key = cfg.get("key", "")
        if key in CONFIG_UPDATES:
            updates = CONFIG_UPDATES[key]
            cfg.update(updates)


def main():
    # Read all files from v2-fixed zip
    files = {}
    with zipfile.ZipFile(BASE_ZIP, "r") as zin:
        for name in zin.namelist():
            files[name] = zin.read(name)

    # Parse element.json
    element_key = BASE_PREFIX + "element.json"
    element = json.loads(files[element_key])

    # 1. Apply config field updates
    apply_config_updates(element.get("configuration", []))

    # 2. Improve parameter displayNames in resources
    apply_param_display_names(element.get("resources", []))

    # Write back element.json
    files[element_key] = json.dumps(element, separators=(",", ":")).encode("utf-8")

    # 3. Update standard-resource files with real fields
    sr_prefix = BASE_PREFIX + "standard-resources/"
    for fname, data in list(files.items()):
        if not fname.startswith(sr_prefix) or not fname.endswith(".json"):
            continue
        sr_name = fname[len(sr_prefix):-len(".json")]
        if sr_name not in FIELDS_BY_RESOURCE:
            continue  # leave key_0 placeholder as-is

        sr = json.loads(data)
        fields = FIELDS_BY_RESOURCE[sr_name]
        sr["fields"] = fields

        # Also fix parameter displayNames inside the resource's resources list
        apply_param_display_names(sr.get("resources", []))

        files[fname] = json.dumps(sr, separators=(",", ":")).encode("utf-8")

    # Write output zip
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    # Copy to downloaded/
    COPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(OUT_PATH, COPY_PATH)

    print(f"Written: {OUT_PATH}")
    print(f"Copied:  {COPY_PATH}")
    print(f"Standard resources with real fields: {sorted(FIELDS_BY_RESOURCE.keys())}")


if __name__ == "__main__":
    main()
