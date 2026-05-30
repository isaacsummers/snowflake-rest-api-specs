#!/usr/bin/env python3
"""
Build UiPath connector zip for Snowflake REST API v5.
Base: snowflake-rest-api-v2-connector-v4.zip

v5 changes vs v4:
  - DescribeThread: add page_size and last_message_id query params to element.json resource
  - DescribeThread: add metadata, messages sub-fields (message_id, parent_id, created_on,
    role, message_payload, request_id) to standard-resource fields
  - Add UpdateThread — POST /api/v2/cortex/threads/{id}
  - Add ListThreads  — GET  /api/v2/cortex/threads
  - Add DeleteThread — DELETE /api/v2/cortex/threads/{id}
  Total: 34 → 37 resources
"""

import copy
import json
import zipfile
import shutil
from pathlib import Path

BASE_ZIP  = Path(__file__).parent.parent / "uipath-ready/v2/snowflake-rest-api-v2-connector-v4.zip"
OUT_PATH  = Path(__file__).parent.parent / "uipath-ready/v2/snowflake-rest-api-v2-connector-v5.zip"
COPY_PATH = Path(__file__).parent.parent / "downloaded/snowflake-rest-api-v2-connector-v5.zip"

BASE_PREFIX = "design-medtronicplc-snowflakerestapi/app/element/"
SR_PREFIX   = BASE_PREFIX + "standard-resources/"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_elem_param(name, vendor_type, data_type, required, display_name, description, sort_order):
    """Build a parameter object matching the shape used in element.json resources."""
    return {
        "vendorName": name,
        "vendorType": vendor_type,
        "name": name,
        "type": vendor_type,
        "description": description,
        "required": required,
        "dataType": data_type,
        "vendorDataType": data_type,
        "source": "request",
        "displayName": display_name,
        "curated": False,
        "sortOrder": sort_order,
    }


def resp_field(name, display_name, native_type, description, sample, method="GETBYID", fmt=None, primary=False):
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
    if primary:
        entry["design"] = {"position": "primary"}
    return entry


def req_field(name, display_name, native_type, description, sample, method="POST",
              required=False, fmt=None, primary=False):
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
# New element.json resource entries
# ---------------------------------------------------------------------------

NEW_ELEMENT_RESOURCES = [
    # UpdateThread — POST /api/v2/cortex/threads/{id}
    {
        "path": "/api/v2/cortex/threads/{id}",
        "vendorPath": "/api/v2/cortex/threads/{id}",
        "method": "POST",
        "vendorMethod": "POST",
        "description": "Updates the name of an existing conversation thread",
        "type": "api",
        "parameters": [
            make_elem_param("id", "path", "integer", True, "Thread ID", "UUID for the thread", 0),
            make_elem_param("body", "body", "object", False, "body", "body", 1),
        ],
        "hooks": [],
        "standardResourceName": "UpdateThread",
        "curated": {
            "name": "UpdateThread",
            "displayName": "Update Thread",
            "description": "Updates the name of an existing conversation thread",
        },
        "operation": "Update",
        "response": {
            "contentType": "application/json",
            "contentTypeAsString": "application/json",
        },
        "createdFromTemplate": False,
    },
    # ListThreads — GET /api/v2/cortex/threads
    {
        "path": "/api/v2/cortex/threads",
        "vendorPath": "/api/v2/cortex/threads",
        "method": "GET",
        "vendorMethod": "GET",
        "description": "Returns all conversation threads belonging to the current user",
        "type": "api",
        "parameters": [
            make_elem_param("origin_application", "query", "string", False,
                            "Origin Application", "Filter threads by originating application name", 0),
        ],
        "hooks": [],
        "standardResourceName": "ListThreads",
        "curated": {
            "name": "ListThreads",
            "displayName": "List Threads",
            "description": "Returns all conversation threads belonging to the current user",
        },
        "operation": "Retrieve",
        "response": {
            "contentType": "application/json",
            "contentTypeAsString": "application/json",
        },
        "createdFromTemplate": False,
    },
    # DeleteThread — DELETE /api/v2/cortex/threads/{id}
    {
        "path": "/api/v2/cortex/threads/{id}",
        "vendorPath": "/api/v2/cortex/threads/{id}",
        "method": "DELETE",
        "vendorMethod": "DELETE",
        "description": "Deletes a thread and all its messages permanently",
        "type": "api",
        "parameters": [
            make_elem_param("id", "path", "integer", True, "Thread ID", "UUID of the thread to delete", 0),
        ],
        "hooks": [],
        "standardResourceName": "DeleteThread",
        "curated": {
            "name": "DeleteThread",
            "displayName": "Delete Thread",
            "description": "Deletes a thread and all its messages permanently",
        },
        "operation": "Delete",
        "response": {
            "contentType": "application/json",
            "contentTypeAsString": "application/json",
        },
        "createdFromTemplate": False,
    },
]

# ---------------------------------------------------------------------------
# New standard-resource file content
# ---------------------------------------------------------------------------

def make_standard_resource(name, display_name, description, path, method_key, http_method,
                             operation, curated_name, curated_display, curated_desc,
                             parameters, fields):
    """Build a standard-resource JSON matching CreateThread.json shape exactly."""
    return {
        "name": name,
        "path": path,
        "type": "standard",
        "subType": "standard",
        "elementKey": "design-medtronicplc-snowflakerestapi",
        "displayName": display_name,
        "custom": "no",
        "deleted": False,
        "metadata": {
            "method": {
                method_key: {
                    "path": path,
                    "method": http_method,
                    "description": description,
                    "operationId": f"{name[0].lower()}{name[1:]}",
                    "operation": operation,
                    "curated": {
                        "name": curated_name,
                        "displayName": curated_display,
                        "description": curated_desc,
                    },
                }
            },
            "bulk": {
                "bulkTypes": [
                    {
                        "direction": "DOWNLOAD",
                        "types": ["NORMALIZED"],
                        "operations": ["Create", "Update"],
                    },
                    {
                        "direction": "UPLOAD",
                        "types": ["NORMALIZED"],
                        "operations": ["Create", "Update"],
                    },
                ]
            },
        },
        "fields": fields,
        "resources": [
            {
                "path": path,
                "vendorPath": path,
                "method": http_method,
                "vendorMethod": http_method,
                "description": description,
                "type": "api",
                "parameters": parameters,
                "hooks": [],
                "standardResourceName": name,
                "curated": {
                    "name": curated_name,
                    "displayName": curated_display,
                    "description": curated_desc,
                },
                "operation": operation,
                "response": {
                    "contentType": "application/json",
                    "contentTypeAsString": "application/json",
                },
                "createdFromTemplate": False,
            }
        ],
        "isPriority": False,
        "isHidden": False,
    }


# UpdateThread standard-resource
UPDATE_THREAD_SR = make_standard_resource(
    name="UpdateThread",
    display_name="Update Thread",
    description="Updates the name of an existing conversation thread",
    path="/api/v2/cortex/threads/{id}",
    method_key="POST",
    http_method="POST",
    operation="Update",
    curated_name="UpdateThread",
    curated_display="Update Thread",
    curated_desc="Updates the name of an existing conversation thread",
    parameters=[
        {
            "vendorName": "id",
            "vendorType": "path",
            "name": "id",
            "type": "path",
            "description": "UUID for the thread",
            "required": True,
            "dataType": "integer",
            "vendorDataType": "integer",
            "source": "request",
            "displayName": "Thread ID",
            "curated": False,
            "sortOrder": 0,
        },
        {
            "vendorName": "body",
            "vendorType": "body",
            "name": "body",
            "type": "body",
            "description": "body",
            "required": False,
            "dataType": "UpdateThread",
            "vendorDataType": "UpdateThread",
            "source": "request",
            "displayName": "body",
            "curated": False,
            "sortOrder": 1,
        },
    ],
    fields={
        "key_0": copy.deepcopy(KEY_0),
        "thread_name": req_field(
            "thread_name", "Thread Name", "string",
            "New name for the thread", "",
            method="POST", required=False, primary=True,
        ),
        "status": resp_field(
            "status", "Status", "string",
            "Result of the update operation", "Thread successfully updated.",
            method="POST",
        ),
    },
)

# ListThreads standard-resource
LIST_THREADS_SR = make_standard_resource(
    name="ListThreads",
    display_name="List Threads",
    description="Returns all conversation threads belonging to the current user",
    path="/api/v2/cortex/threads",
    method_key="GET",
    http_method="GET",
    operation="Retrieve",
    curated_name="ListThreads",
    curated_display="List Threads",
    curated_desc="Returns all conversation threads belonging to the current user",
    parameters=[
        {
            "vendorName": "origin_application",
            "vendorType": "query",
            "name": "origin_application",
            "type": "query",
            "description": "Filter threads by originating application name",
            "required": False,
            "dataType": "string",
            "vendorDataType": "string",
            "source": "request",
            "displayName": "Origin Application",
            "curated": False,
            "sortOrder": 0,
        },
    ],
    fields={
        "key_0": copy.deepcopy(KEY_0),
        "data": resp_field(
            "data", "Threads", "array",
            "Array of thread metadata objects", [],
            method="GET", primary=True,
        ),
    },
)

# DeleteThread standard-resource
DELETE_THREAD_SR = make_standard_resource(
    name="DeleteThread",
    display_name="Delete Thread",
    description="Deletes a thread and all its messages permanently",
    path="/api/v2/cortex/threads/{id}",
    method_key="DELETE",
    http_method="DELETE",
    operation="Delete",
    curated_name="DeleteThread",
    curated_display="Delete Thread",
    curated_desc="Deletes a thread and all its messages permanently",
    parameters=[
        {
            "vendorName": "id",
            "vendorType": "path",
            "name": "id",
            "type": "path",
            "description": "UUID of the thread to delete",
            "required": True,
            "dataType": "integer",
            "vendorDataType": "integer",
            "source": "request",
            "displayName": "Thread ID",
            "curated": False,
            "sortOrder": 0,
        },
    ],
    fields={
        "key_0": copy.deepcopy(KEY_0),
        "success": resp_field(
            "success", "Success", "boolean",
            "True if the thread was deleted successfully", True,
            method="DELETE", primary=True,
        ),
    },
)

# ---------------------------------------------------------------------------
# DescribeThread: additional fields (message sub-fields + metadata)
# ---------------------------------------------------------------------------

DESCRIBE_THREAD_EXTRA_FIELDS = {
    "metadata": resp_field(
        "metadata", "Metadata", "object",
        "Thread metadata object.", {},
        method="GETBYID",
    ),
    "message_id": resp_field(
        "message_id", "Message ID", "integer",
        "Unique identifier for a message in the thread.", 0,
        method="GETBYID", fmt="int64",
    ),
    "parent_id": resp_field(
        "parent_id", "Parent ID", "integer",
        "ID of the parent message (for threaded replies).", 0,
        method="GETBYID", fmt="int64",
    ),
    "message_created_on": resp_field(
        "message_created_on", "Message Created On", "integer",
        "Unix timestamp (ms) when the message was created.", 0,
        method="GETBYID", fmt="int64",
    ),
    "role": resp_field(
        "role", "Role", "string",
        "Role of the message author (user or assistant).", "",
        method="GETBYID",
    ),
    "message_payload": resp_field(
        "message_payload", "Message Payload", "string",
        "Content payload of the message.", "",
        method="GETBYID",
    ),
    "request_id": resp_field(
        "request_id", "Request ID", "string",
        "Request ID associated with the message.", "",
        method="GETBYID",
    ),
}

# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def main():
    # Read all files from v4 zip
    files = {}
    with zipfile.ZipFile(BASE_ZIP, "r") as zin:
        for name in zin.namelist():
            files[name] = zin.read(name)

    # ---- 1. Patch element.json ------------------------------------------------
    element_key = BASE_PREFIX + "element.json"
    element = json.loads(files[element_key])

    # Fix DescribeThread resource: add page_size and last_message_id query params
    for res in element["resources"]:
        if res.get("path") == "/api/v2/cortex/threads/{id}" and res.get("method") == "GET":
            existing_names = {p["name"] for p in res.get("parameters", [])}
            if "page_size" not in existing_names:
                res["parameters"].append(
                    make_elem_param(
                        "page_size", "query", "integer", False,
                        "Page Size",
                        "Number of messages to return (default: 20, max: 100)",
                        len(res["parameters"]),
                    )
                )
            if "last_message_id" not in existing_names:
                res["parameters"].append(
                    make_elem_param(
                        "last_message_id", "query", "integer", False,
                        "Last Message ID",
                        "ID of the last message received, used for pagination",
                        len(res["parameters"]),
                    )
                )
            break

    # Add 3 new resources
    element["resources"].extend(NEW_ELEMENT_RESOURCES)
    files[element_key] = json.dumps(element, separators=(",", ":")).encode("utf-8")

    # ---- 2. Patch DescribeThread.json ----------------------------------------
    dt_key = SR_PREFIX + "DescribeThread.json"
    dt = json.loads(files[dt_key])

    # Add metadata and message sub-fields (keep existing fields intact)
    for fname, fval in DESCRIBE_THREAD_EXTRA_FIELDS.items():
        if fname not in dt["fields"]:
            dt["fields"][fname] = fval

    files[dt_key] = json.dumps(dt, separators=(",", ":")).encode("utf-8")

    # ---- 3. Add new standard-resource files ----------------------------------
    for sr_name, sr_data in [
        ("UpdateThread", UPDATE_THREAD_SR),
        ("ListThreads",  LIST_THREADS_SR),
        ("DeleteThread", DELETE_THREAD_SR),
    ]:
        files[SR_PREFIX + f"{sr_name}.json"] = json.dumps(sr_data, separators=(",", ":")).encode("utf-8")

    # ---- 4. Write output zip -------------------------------------------------
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    COPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_PATH, COPY_PATH)

    # ---- 5. Verify -----------------------------------------------------------
    print("=== v5 Build Complete ===")
    print(f"Written: {OUT_PATH}")
    print(f"Copied:  {COPY_PATH}")

    with zipfile.ZipFile(OUT_PATH, "r") as zcheck:
        elem_check = json.loads(zcheck.read(BASE_PREFIX + "element.json"))
        resource_count = len(elem_check["resources"])
        print(f"\nTotal resources in element.json: {resource_count}")

        # List thread-related resources
        print("\nThread resources:")
        for res in elem_check["resources"]:
            if "thread" in res.get("path", "").lower():
                sr_name = res.get("standardResourceName", "?")
                params = [p["name"] for p in res.get("parameters", [])]
                print(f"  [{res['method']}] {res['path']}  →  {sr_name}  params={params}")

        # Spot-check DescribeThread fields
        dt_check = json.loads(zcheck.read(SR_PREFIX + "DescribeThread.json"))
        print(f"\nDescribeThread fields: {sorted(dt_check['fields'].keys())}")

        # List new SR files
        for sr_name in ["UpdateThread", "ListThreads", "DeleteThread"]:
            sr = json.loads(zcheck.read(SR_PREFIX + f"{sr_name}.json"))
            print(f"\n{sr_name} fields: {sorted(sr['fields'].keys())}")

    if resource_count != 37:
        print(f"\n⚠️  Expected 37 resources, got {resource_count}")
    else:
        print("\n✅ Resource count: 37 confirmed")


if __name__ == "__main__":
    main()
