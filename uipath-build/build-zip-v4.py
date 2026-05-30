#!/usr/bin/env python3
"""
Build UiPath connector zip for Snowflake REST API v4.
Base: design-medtronicplc-snowflakerestapi-v2-fixed-2.zip (Isaac's curated baseline).

v4 changes vs v3:
  - CreateThread fields copied verbatim from Isaac's curated version (already in base)
  - Curated metadata blocks (metadata.method.curated + resource.curated) added to ALL activities
  - Real fields with request/response/required/requestCurated/responseCurated flags on ALL activities
  - event.notification.basic.username and connection.name hidden (only 4 visible config fields)
  - design.position: primary on the most important request field per activity
"""

import copy
import json
import zipfile
import shutil
from pathlib import Path

BASE_ZIP = Path("/mnt/windows/Downloads/design-medtronicplc-snowflakerestapi-v2-fixed-2.zip")
OUT_PATH = Path(__file__).parent.parent / "uipath-ready/v2/snowflake-rest-api-v2-connector-v4.zip"
COPY_PATH = Path(__file__).parent.parent / "downloaded/snowflake-rest-api-v2-connector-v4.zip"

KEY_0 = {
    "method": {"POST": {"name": "POST"}},
    "displayName": "Key_0",
    "nativeType": "number",
    "custom": "no",
    "name": "key_0",
    "format": "double",
    "description": "The Key",
    "type": "number",
    "sampleValue": 1737.7815901989036,
}

# ---------------------------------------------------------------------------
# Field builders — matching Isaac's curated pattern exactly
# ---------------------------------------------------------------------------

def req_resp_field(name, display_name, native_type, description, sample, method="POST",
                    required=False, fmt=None, primary=False):
    """A field that appears in both request and response."""
    entry = {
        "method": {method: {
            "name": method,
            "request": True,
            "response": True,
            "required": required,
            "requestCurated": True,
            "responseCurated": True,
        }},
        "displayName": display_name,
        "nativeType": native_type,
        "custom": "no",
        "name": name,
        "description": description,
        "type": native_type,
        "sampleValue": sample,
    }
    if fmt:
        entry["format"] = fmt
    if primary:
        entry["design"] = {"position": "primary"}
    return entry


def req_field(name, display_name, native_type, description, sample, method="POST",
               required=True, fmt=None, primary=False):
    """A request-only field."""
    entry = {
        "method": {method: {
            "name": method,
            "request": True,
            "required": required,
            "requestCurated": True,
        }},
        "displayName": display_name,
        "nativeType": native_type,
        "custom": "no",
        "name": name,
        "description": description,
        "type": native_type,
        "sampleValue": sample,
    }
    if fmt:
        entry["format"] = fmt
    if primary:
        entry["design"] = {"position": "primary"}
    return entry


def resp_field(name, display_name, native_type, description, sample, method="POST", fmt=None):
    """A response-only field."""
    entry = {
        "method": {method: {
            "name": method,
            "response": True,
            "responseCurated": True,
        }},
        "displayName": display_name,
        "nativeType": native_type,
        "custom": "no",
        "name": name,
        "description": description,
        "type": native_type,
        "sampleValue": sample,
    }
    if fmt:
        entry["format"] = fmt
    return entry


# ---------------------------------------------------------------------------
# Field definitions — all activities
# (CreateThread fields are kept verbatim from Isaac's curated baseline)
# ---------------------------------------------------------------------------

# Shared streaming-only fields (no structured response, keep key_0 only)
def streaming_fields(method="POST"):
    return {"key_0": copy.deepcopy(KEY_0)}


FIELDS_BY_RESOURCE = {

    # -- Agent operations -------------------------------------------------------

    "AgentRun": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Conversation messages to send to the agent.", [], primary=True),
        "stream": req_field("stream", "Stream Response", "boolean",
            "Stream the response via SSE (default: true).", True, required=False),
        "thread_id": req_field("thread_id", "Thread ID", "integer",
            "Optional thread ID for conversation continuity.", 0, required=False, fmt="int64"),
        "parent_message_id": req_field("parent_message_id", "Parent Message ID", "integer",
            "Optional parent message ID.", 0, required=False, fmt="int64"),
        "tools": req_field("tools", "Tools", "array",
            "Tools available to the agent.", [], required=False),
        "tool_resources": req_field("tool_resources", "Tool Resources", "object",
            "Resources for agent tools.", {}, required=False),
        "tool_choice": req_field("tool_choice", "Tool Choice", "object",
            "Tool selection control.", {}, required=False),
    },

    "AgentRunWithObject": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Conversation messages to send to the named agent object.", [], primary=True),
        "stream": req_field("stream", "Stream Response", "boolean",
            "Stream the response via SSE (default: true).", True, required=False),
        "thread_id": req_field("thread_id", "Thread ID", "integer",
            "Optional thread ID for conversation continuity.", 0, required=False, fmt="int64"),
        "parent_message_id": req_field("parent_message_id", "Parent Message ID", "integer",
            "Optional parent message ID.", 0, required=False, fmt="int64"),
        "tools": req_field("tools", "Tools", "array",
            "Tool overrides for this run.", [], required=False),
        "tool_resources": req_field("tool_resources", "Tool Resources", "object",
            "Resources for agent tools.", {}, required=False),
        "tool_choice": req_field("tool_choice", "Tool Choice", "object",
            "Tool selection control.", {}, required=False),
    },

    "AgentFeedback": {
        "key_0": copy.deepcopy(KEY_0),
        "positive": req_field("positive", "Positive", "boolean",
            "Whether the feedback is positive (true) or negative (false).", True,
            required=True, primary=True),
        "feedback_message": req_field("feedback_message", "Feedback Message", "string",
            "Optional free-text feedback message.", "", required=False),
        "orig_request_id": req_field("orig_request_id", "Original Request ID", "string",
            "Request ID of the agent response being rated.", "", required=False),
        "categories": req_field("categories", "Categories", "array",
            "Feedback category labels.", [], required=False),
        "thread_id": req_field("thread_id", "Thread ID", "integer",
            "Thread ID associated with the response.", 0, required=False, fmt="int64"),
    },

    # -- Cortex Analyst ---------------------------------------------------------

    "CortexAnalyst_sendMessage": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Conversation messages. Each has 'role' (user|analyst) and 'content' array.",
            [], required=True, primary=True),
        "semantic_model_file": req_field("semantic_model_file", "Semantic Model File", "string",
            "Stage path to semantic model YAML, e.g. @db.schema.stage/path/file.yaml.",
            "", required=False),
        "semantic_model": req_field("semantic_model", "Semantic Model (inline)", "string",
            "Inline YAML string for the semantic model.", "", required=False),
        "stream": req_field("stream", "Stream Response", "boolean",
            "Stream the response (default: false for structured JSON).", False, required=False),
        "message": resp_field("message", "Response Message", "object",
            "The analyst response message object.", {}),
        "request_id": resp_field("request_id", "Request ID", "string",
            "Unique request identifier for the analyst call.", ""),
    },

    "CortexAnalyst_sendFeedback": {
        "key_0": copy.deepcopy(KEY_0),
        "request_id": req_field("request_id", "Request ID", "string",
            "Request ID from the analyst response to rate.", "", required=True, primary=True),
        "positive": req_field("positive", "Positive", "boolean",
            "Whether the feedback is positive (true) or negative (false).", True, required=True),
        "feedback_message": req_field("feedback_message", "Feedback Message", "string",
            "Optional free-text feedback note.", "", required=False),
    },

    "CortexAnalyst_fastGeneration": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Input messages or source material for fast semantic model generation.",
            [], required=True, primary=True),
    },

    "CortexAnalyst_generateFiltersAndMetricsSuggestions": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Messages providing context for filter and metric suggestion generation.",
            [], required=True, primary=True),
    },

    "CortexAnalyst_generateVerifiedQuerySuggestions": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Messages providing context for verified query suggestion generation.",
            [], required=True, primary=True),
    },

    "CortexAnalyst_getAgenticOptimization": {
        "key_0": copy.deepcopy(KEY_0),
    },

    "CortexAnalyst_getScopedToken": {
        "key_0": copy.deepcopy(KEY_0),
    },

    "CortexAnalyst_listAgenticOptimizations": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Input messages for listing agentic optimization runs.",
            [], required=True, primary=True),
    },

    "CortexAnalyst_preSelection": {
        "key_0": copy.deepcopy(KEY_0),
        "messages": req_field("messages", "Messages", "array",
            "Input data or context for pre-selection of relevant table information.",
            [], required=True, primary=True),
    },

    # -- Cortex Inference / LLM -------------------------------------------------

    "CortexInference_cortexLLMInferenceComplete": {
        "key_0": copy.deepcopy(KEY_0),
        "model": req_field("model", "Model", "string",
            "Model name, e.g. 'claude-3-5-sonnet', 'mistral-large2', 'llama3.1-70b'.",
            "", required=True, primary=True),
        "messages": req_field("messages", "Messages", "array",
            "Conversation messages. Each has 'role' and 'content'.", [], required=True),
        "stream": req_field("stream", "Stream Response", "boolean",
            "Stream the response via SSE.", False, required=False),
        "max_tokens": req_field("max_tokens", "Max Tokens", "integer",
            "Maximum output tokens to generate.", 0, required=False, fmt="int32"),
        "temperature": req_field("temperature", "Temperature", "number",
            "Randomness control: 0 = deterministic, higher = more creative.",
            0.0, required=False, fmt="double"),
        "top_p": req_field("top_p", "Top P", "number",
            "Nucleus sampling threshold. Typical values: 0.9–1.0.",
            0.0, required=False, fmt="double"),
    },

    "CortexInference_getModels": {
        "key_0": copy.deepcopy(KEY_0),
        "models": resp_field("models", "Models", "array",
            "List of available LLM model objects.", [], method="GETBYID"),
    },

    "CortexOpenAI_cortexGenericOpenAIChatCompletions": {
        "key_0": copy.deepcopy(KEY_0),
        "model": req_field("model", "Model", "string",
            "Model name for OpenAI-compatible chat completions.", "", required=True, primary=True),
        "messages": req_field("messages", "Messages", "array",
            "Array of chat messages with 'role' and 'content' fields.", [], required=True),
        "stream": req_field("stream", "Stream Response", "boolean",
            "Stream the response via SSE.", False, required=False),
        "max_tokens": req_field("max_tokens", "Max Tokens", "integer",
            "Maximum tokens in the completion.", 0, required=False, fmt="int32"),
        "temperature": req_field("temperature", "Temperature", "number",
            "Sampling temperature. 0 = deterministic.", 0.0, required=False, fmt="double"),
        "top_p": req_field("top_p", "Top P", "number",
            "Nucleus sampling threshold.", 0.0, required=False, fmt="double"),
    },

    "CortexAnthropic_cortexGenericAnthropicMessages": {
        "key_0": copy.deepcopy(KEY_0),
        "model": req_field("model", "Model", "string",
            "Model name for Anthropic-compatible Messages API.", "", required=True, primary=True),
        "messages": req_field("messages", "Messages", "array",
            "Array of messages with 'role' and 'content' fields.", [], required=True),
        "max_tokens": req_field("max_tokens", "Max Tokens", "integer",
            "Maximum tokens to generate (required by Anthropic API).", 0,
            required=True, fmt="int32"),
        "stream": req_field("stream", "Stream Response", "boolean",
            "Stream the response via SSE.", False, required=False),
        "system": req_field("system", "System Prompt", "string",
            "System prompt string or array of content blocks.", "", required=False),
    },

    "CortexEmbed_embed": {
        "key_0": copy.deepcopy(KEY_0),
        "model": req_field("model", "Model", "string",
            "Embedding model name, e.g. 'snowflake-arctic-embed-m-v1.5'.",
            "", required=True, primary=True),
        "input": req_field("input", "Input Texts", "array",
            "Array of strings to embed.", [], required=True),
        "data": resp_field("data", "Embedding Data", "array",
            "Array of embedding objects with 'embedding' float arrays.", []),
        "usage": resp_field("usage", "Usage", "object",
            "Token usage statistics for the embed call.", {}),
    },

    # -- SQL API ----------------------------------------------------------------

    "SqlApi_SubmitStatement": {
        "key_0": copy.deepcopy(KEY_0),
        "statement": req_field("statement", "SQL Statement", "string",
            "SQL statement to execute. DML, DDL, and queries supported.",
            "", required=True, primary=True),
        "timeout": req_field("timeout", "Timeout (seconds)", "integer",
            "Execution timeout in seconds. 0 = maximum (604800).",
            0, required=False, fmt="int64"),
        "database": req_field("database", "Database", "string",
            "Database context for statement execution (case-sensitive).",
            "", required=False),
        "schema": req_field("schema", "Schema", "string",
            "Schema context for statement execution (case-sensitive).",
            "", required=False),
        "warehouse": req_field("warehouse", "Warehouse", "string",
            "Warehouse to use for statement execution (case-sensitive).",
            "", required=False),
        "role": req_field("role", "Role", "string",
            "Role to use for statement execution (case-sensitive).",
            "", required=False),
        "parameters": req_field("parameters", "Session Parameters", "object",
            "Session parameters to set before executing (e.g. timezone, query_tag).",
            {}, required=False),
        "bindings": req_field("bindings", "Bind Variables", "object",
            "Values for bind variables in the SQL statement (? or :name placeholders).",
            {}, required=False),
        "statementHandle": resp_field("statementHandle", "Statement Handle", "string",
            "Unique handle to check status of async statement execution.", ""),
        "statementStatusUrl": resp_field("statementStatusUrl", "Statement Status URL", "string",
            "URL to poll for statement execution status.", ""),
        "message": resp_field("message", "Message", "string",
            "Informational message about the statement execution.", ""),
        "sqlState": resp_field("sqlState", "SQL State", "string",
            "SQLSTATE code from the statement execution.", ""),
    },

    "SqlApi_GetStatementStatus": {
        "key_0": copy.deepcopy(KEY_0),
        "statementHandle": resp_field("statementHandle", "Statement Handle", "string",
            "The statement handle for this result.", "", method="GETBYID"),
        "message": resp_field("message", "Message", "string",
            "Execution status message.", "", method="GETBYID"),
        "sqlState": resp_field("sqlState", "SQL State", "string",
            "SQLSTATE code from execution.", "", method="GETBYID"),
        "data": resp_field("data", "Result Data", "array",
            "Array of result rows (list of lists).", [], method="GETBYID"),
        "resultSetMetaData": resp_field("resultSetMetaData", "Result Set Metadata", "object",
            "Metadata about the result set columns and format.", {}, method="GETBYID"),
    },

    "SqlApi_CancelStatement": {
        "key_0": copy.deepcopy(KEY_0),
    },

    # -- Thread / Agent CRUD ----------------------------------------------------
    # CreateThread: fields already curated in base zip — DO NOT OVERRIDE
    # (handled specially below to preserve Isaac's exact version)

    "DescribeThread": {
        "key_0": copy.deepcopy(KEY_0),
        "thread_id": resp_field("thread_id", "Thread ID", "integer",
            "Unique identifier for the thread.", 0, method="GETBYID", fmt="int64"),
        "thread_name": resp_field("thread_name", "Thread Name", "string",
            "Name of the thread.", "", method="GETBYID"),
        "origin_application": resp_field("origin_application", "Origin Application", "string",
            "Application that created the thread.", "", method="GETBYID"),
        "created_on": resp_field("created_on", "Created On", "integer",
            "Unix timestamp (ms) when the thread was created.", 0, method="GETBYID", fmt="int64"),
        "updated_on": resp_field("updated_on", "Updated On", "integer",
            "Unix timestamp (ms) when the thread was last updated.", 0, method="GETBYID", fmt="int64"),
        "messages": resp_field("messages", "Messages", "array",
            "Array of messages in the thread.", [], method="GETBYID"),
    },

    "CreateAgent": {
        "key_0": copy.deepcopy(KEY_0),
        "name": req_field("name", "Agent Name", "string",
            "Name of the Cortex Agent object to create.", "", required=True, primary=True),
        "comment": req_field("comment", "Comment", "string",
            "Optional description or comment for the agent.", "", required=False),
        "profile": req_field("profile", "Profile", "object",
            "Agent profile configuration object.", {}, required=False),
        "models": req_field("models", "Models", "object",
            "Model configuration for the agent.", {}, required=False),
        "instructions": req_field("instructions", "Instructions", "object",
            "Instructions that define agent behavior.", {}, required=False),
        "tools": req_field("tools", "Tools", "array",
            "Tools available to the agent.", [], required=False),
        "tool_resources": req_field("tool_resources", "Tool Resources", "object",
            "Resources for agent tools.", {}, required=False),
        "status": resp_field("status", "Status", "string",
            "Result status of the create operation.", ""),
    },

    "DescribeAgent": {
        "key_0": copy.deepcopy(KEY_0),
        "name": resp_field("name", "Agent Name", "string",
            "Name of the agent.", "", method="GETBYID"),
        "comment": resp_field("comment", "Comment", "string",
            "Agent comment or description.", "", method="GETBYID"),
        "profile": resp_field("profile", "Profile", "object",
            "Agent profile configuration.", {}, method="GETBYID"),
        "models": resp_field("models", "Models", "object",
            "Model configuration.", {}, method="GETBYID"),
        "tools": resp_field("tools", "Tools", "array",
            "Tools configured for the agent.", [], method="GETBYID"),
    },

    "DeleteAgent": {
        "key_0": copy.deepcopy(KEY_0),
        "status": resp_field("status", "Status", "string",
            "Result status of the delete operation.", "", method="DELETE"),
    },

    # -- Cortex Search ----------------------------------------------------------

    "CortexSearch_queryCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "query": req_field("query", "Query", "string",
            "Unstructured text query for semantic search.", "", required=True, primary=True),
        "columns": req_field("columns", "Columns", "array",
            "List of column names to include in the results.", [], required=False),
        "filter": req_field("filter", "Filter", "object",
            "Filter expression to narrow search results.", {}, required=False),
        "limit": req_field("limit", "Limit", "integer",
            "Maximum number of results to return.", 0, required=False, fmt="int32"),
        "results": resp_field("results", "Results", "array",
            "Array of search result objects.", []),
        "request_id": resp_field("request_id", "Request ID", "string",
            "Unique request identifier for this search call.", ""),
    },

    "CortexSearch_suggestCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "query": req_field("query", "Query", "string",
            "Partial query string for search suggestion generation.",
            "", required=True, primary=True),
        "max_suggestions": req_field("max_suggestions", "Max Suggestions", "integer",
            "Maximum number of suggestions to return.", 0, required=False, fmt="int32"),
        "suggestions": resp_field("suggestions", "Suggestions", "array",
            "Array of suggested query completions.", []),
    },

    "CortexSearch_createCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "name": req_field("name", "Service Name", "string",
            "Name for the new Cortex Search service.", "", required=True, primary=True),
        "warehouse": req_field("warehouse", "Warehouse", "string",
            "Warehouse to use for indexing the search service.", "", required=True),
        "target_lag": req_field("target_lag", "Target Lag", "string",
            "Target data freshness lag (e.g. '1 minute', '1 hour').", "", required=False),
        "comment": req_field("comment", "Comment", "string",
            "Optional description for the search service.", "", required=False),
        "status": resp_field("status", "Status", "string",
            "Result status of the create operation.", ""),
    },

    "CortexSearch_fetchCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "name": resp_field("name", "Service Name", "string",
            "Name of the search service.", "", method="GETBYID"),
        "state": resp_field("state", "State", "string",
            "Current state of the search service (e.g. ACTIVE, SUSPENDED).", "", method="GETBYID"),
        "created_on": resp_field("created_on", "Created On", "string",
            "Timestamp when the service was created.", "", method="GETBYID"),
        "database_name": resp_field("database_name", "Database Name", "string",
            "Database the service belongs to.", "", method="GETBYID"),
        "schema_name": resp_field("schema_name", "Schema Name", "string",
            "Schema the service belongs to.", "", method="GETBYID"),
    },

    "CortexSearch_listCortexSearchServices": {
        "key_0": copy.deepcopy(KEY_0),
        "data": resp_field("data", "Services", "array",
            "Array of Cortex Search service summary objects.", [], method="GETBYID"),
    },

    "CortexSearch_deleteCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "status": resp_field("status", "Status", "string",
            "Result status of the delete operation.", "", method="DELETE"),
    },

    "CortexSearch_suspendCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "status": resp_field("status", "Status", "string",
            "Result status of the suspend operation.", ""),
    },

    "CortexSearch_resumeCortexSearchService": {
        "key_0": copy.deepcopy(KEY_0),
        "status": resp_field("status", "Status", "string",
            "Result status of the resume operation.", ""),
    },

    "CortexSearch_sendFeedback": {
        "key_0": copy.deepcopy(KEY_0),
        "query": req_field("query", "Query", "string",
            "The query string associated with the result being rated.",
            "", required=True, primary=True),
        "positive": req_field("positive", "Positive", "boolean",
            "Whether the result was relevant (true) or not (false).", True, required=True),
        "result_id": req_field("result_id", "Result ID", "string",
            "ID of the search result being rated.", "", required=False),
    },
}

# ---------------------------------------------------------------------------
# Curated display names — operationId → (name, displayName, description)
# ---------------------------------------------------------------------------

CURATED_META = {
    "AgentRun":             ("RunCortexAgent",       "Run Cortex Agent",             "Run a Cortex Agent without a named agent object."),
    "AgentRunWithObject":   ("RunNamedCortexAgent",  "Run Named Cortex Agent",        "Run a Cortex Agent using a named agent object."),
    "AgentFeedback":        ("SubmitAgentFeedback",  "Submit Agent Feedback",         "Submit feedback on a Cortex Agent response."),
    "CortexAnalyst_sendMessage":    ("SendAnalystMessage",  "Send Analyst Message",   "Send a natural-language data question to Cortex Analyst."),
    "CortexAnalyst_sendFeedback":   ("SendAnalystFeedback", "Send Analyst Feedback",  "Submit feedback on a Cortex Analyst response."),
    "CortexAnalyst_fastGeneration": ("AnalystFastGeneration", "Analyst Fast Generation", "Rapidly generate a semantic model from source material."),
    "CortexAnalyst_generateFiltersAndMetricsSuggestions": ("AnalystFilterMetricSuggestions", "Analyst Filter & Metric Suggestions", "Generate filter and metric suggestions for a semantic model."),
    "CortexAnalyst_generateVerifiedQuerySuggestions":     ("AnalystVerifiedQuerySuggestions", "Analyst Verified Query Suggestions", "Generate verified query suggestions for a semantic model."),
    "CortexAnalyst_getAgenticOptimization":  ("GetAgenticOptimization",   "Get Agentic Optimization",    "Get the status and state of a specified agentic optimization run."),
    "CortexAnalyst_getScopedToken":          ("GetAnalystScopedToken",     "Get Analyst Scoped Token",    "Exchange a Cortex Analyst OAuth token for a scoped token."),
    "CortexAnalyst_listAgenticOptimizations":("ListAgenticOptimizations",  "List Agentic Optimizations",  "List all agentic optimization runs for a given base model."),
    "CortexAnalyst_preSelection":            ("AnalystPreSelection",       "Analyst Pre-Selection",       "Retrieve relevant table information for semantic model generation."),
    "CortexInference_cortexLLMInferenceComplete": ("LLMComplete",          "LLM Complete",                "Perform LLM text completion inference via Cortex."),
    "CortexInference_getModels":             ("ListAvailableModels",       "List Available Models",       "Return the LLMs available for the current Snowflake session."),
    "CortexOpenAI_cortexGenericOpenAIChatCompletions": ("ChatCompletionsOpenAI", "Chat Completions (OpenAI Format)", "Perform LLM inference using the OpenAI-compatible chat completions format."),
    "CortexAnthropic_cortexGenericAnthropicMessages":  ("MessagesAnthropic",   "Messages (Anthropic Format)",      "Perform LLM inference using the Anthropic-compatible messages format."),
    "CortexEmbed_embed":                     ("EmbedText",                "Embed Text",                   "Generate vector embeddings for an array of text strings."),
    "CortexSearch_queryCortexSearchService": ("QuerySearchService",        "Query Search Service",         "Run a semantic search query against a Cortex Search Service."),
    "CortexSearch_suggestCortexSearchService": ("GetSearchSuggestions",   "Get Search Suggestions",       "Get autocomplete suggestions from a Cortex Search Service."),
    "CortexSearch_createCortexSearchService": ("CreateSearchService",     "Create Search Service",        "Create a new Cortex Search Service."),
    "CortexSearch_fetchCortexSearchService":  ("GetSearchService",        "Get Search Service",           "Fetch details for a Cortex Search Service."),
    "CortexSearch_listCortexSearchServices":  ("ListSearchServices",      "List Search Services",         "List Cortex Search Services in a database schema."),
    "CortexSearch_deleteCortexSearchService": ("DeleteSearchService",     "Delete Search Service",        "Delete a Cortex Search Service."),
    "CortexSearch_suspendCortexSearchService":("SuspendSearchService",    "Suspend Search Service",       "Suspend a Cortex Search Service."),
    "CortexSearch_resumeCortexSearchService": ("ResumeSearchService",     "Resume Search Service",        "Resume a suspended Cortex Search Service."),
    "CortexSearch_sendFeedback":              ("SendSearchFeedback",       "Send Search Feedback",         "Submit relevance feedback on a Cortex Search result."),
    "SqlApi_SubmitStatement":                 ("ExecuteSQLStatement",      "Execute SQL Statement",        "Submit a SQL statement for execution via the Snowflake SQL API."),
    "SqlApi_GetStatementStatus":              ("GetStatementStatus",       "Get Statement Status",         "Check the execution status of a submitted SQL statement."),
    "SqlApi_CancelStatement":                 ("CancelStatement",          "Cancel Statement",             "Cancel the execution of a running SQL statement."),
    "CreateThread":                           ("CreateNewConversationThread", "Create New Conversation Thread", "Create a new conversation thread_id for cortex agents."),
    "DescribeThread":                         ("GetThreadMessages",        "Get Thread Messages",          "Retrieve a thread and its message history."),
    "CreateAgent":                            ("CreateCortexAgent",        "Create Cortex Agent",          "Create a new named Cortex Agent object."),
    "DescribeAgent":                          ("GetCortexAgent",           "Get Cortex Agent",             "Retrieve details for a named Cortex Agent object."),
    "DeleteAgent":                            ("DeleteCortexAgent",        "Delete Cortex Agent",          "Delete a named Cortex Agent object."),
}

# Config fields that should be hidden (only 4 visible: orgname-accountname, oauth.api.key, oauth.api.secret, oauth.scope)
HIDE_CONFIG_KEYS = {"event.notification.basic.username", "connection.name"}


def apply_curated(sr: dict, name: str):
    """Inject curated block into metadata.method and resources[0]."""
    if name not in CURATED_META:
        return
    c_name, c_display, c_desc = CURATED_META[name]
    curated_block = {"name": c_name, "displayName": c_display, "description": c_desc}

    # metadata.method — inject into each method block
    for method_key, method_val in sr.get("metadata", {}).get("method", {}).items():
        method_val["curated"] = curated_block

    # resources[0]
    resources = sr.get("resources", [])
    if resources:
        resources[0]["curated"] = curated_block


def main():
    # Read all files from base zip (Isaac's curated v2-fixed-2)
    files = {}
    with zipfile.ZipFile(BASE_ZIP, "r") as zin:
        for name in zin.namelist():
            files[name] = zin.read(name)

    BASE_PREFIX = "design-medtronicplc-snowflakerestapi/app/element/"
    element_key = BASE_PREFIX + "element.json"

    # -- element.json: fix config visibility -----------------------------------
    element = json.loads(files[element_key])
    for cfg in element.get("configuration", []):
        if cfg.get("key") in HIDE_CONFIG_KEYS:
            cfg["hide"] = True
    files[element_key] = json.dumps(element, separators=(",", ":")).encode("utf-8")

    # -- standard-resources: apply fields + curated blocks --------------------
    sr_prefix = BASE_PREFIX + "standard-resources/"
    for fname in list(files.keys()):
        if not fname.startswith(sr_prefix) or not fname.endswith(".json"):
            continue
        sr_name = fname[len(sr_prefix):-len(".json")]
        sr = json.loads(files[fname])

        # Apply field definitions (skip CreateThread — already curated in base)
        if sr_name != "CreateThread" and sr_name in FIELDS_BY_RESOURCE:
            sr["fields"] = FIELDS_BY_RESOURCE[sr_name]

        # Apply curated blocks to all resources
        apply_curated(sr, sr_name)

        files[fname] = json.dumps(sr, separators=(",", ":")).encode("utf-8")

    # Write output zip
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    # Copy
    COPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_PATH, COPY_PATH)

    resources_with_real_fields = sorted(
        k for k in FIELDS_BY_RESOURCE
        if len(FIELDS_BY_RESOURCE[k]) > 1  # more than just key_0
    )
    # CreateThread is also curated (from base)
    print("=== v4 Build Complete ===")
    print(f"Written: {OUT_PATH}")
    print(f"Copied:  {COPY_PATH}")
    print(f"\nResources with real fields ({len(resources_with_real_fields)} + CreateThread from base):")
    for r in resources_with_real_fields:
        count = len(FIELDS_BY_RESOURCE[r])
        print(f"  {r}: {count} fields")
    print("\nCreateThread: preserved verbatim from Isaac's curated baseline")
    print("\nVisible config fields (hide=False):")
    element_check = json.loads(files[element_key])
    for cfg in element_check.get("configuration", []):
        if not cfg.get("hide", False):
            print(f"  {cfg['key']} — {cfg['name']}")


if __name__ == "__main__":
    main()
