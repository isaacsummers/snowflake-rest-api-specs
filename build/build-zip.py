#!/usr/bin/env python3
"""
Build a UiPath Integration Service connector zip from the merged Snowflake REST API spec.

Output: uipath-ready/v2/snowflake-rest-api-v2-connector.zip
Structure:
    app/element/element.json
    app/element/element-metadata.json
    app/element/webhook.json
    app/element/standard-resources/<OperationId>.json
"""
from __future__ import annotations

import copy
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path

import yaml

SPEC_PATH = Path("/home/ubuntu/projects/snowflake-rest-api-specs/uipath-ready/v2/snowflake-rest-api-v2.yaml")
ZIP_PATH = Path("/home/ubuntu/projects/snowflake-rest-api-specs/uipath-ready/v2/snowflake-rest-api-v2-connector.zip")

ELEMENT_KEY = "design-medtronicplc-snowflakerestapi"


def to_pascal(s: str) -> str:
    """Capitalise the first letter of a string (leave rest as-is)."""
    return s[0].upper() + s[1:] if s else s


def operation_to_crud(method: str) -> str:
    return {
        "POST": "Create",
        "GET": "Retrieve",
        "DELETE": "Delete",
        "PUT": "Update",
        "PATCH": "Update",
    }.get(method.upper(), "Create")


def build_resource_entry(path: str, method: str, op: dict) -> dict:
    op_id = op["operationId"]
    summary = op.get("summary") or op.get("x-ms-summary") or op_id
    has_body = method.upper() in ("POST", "PUT", "PATCH")
    pascal_op_id = to_pascal(op_id)
    return {
        "path": path,
        "vendorPath": path,
        "method": method.upper(),
        "vendorMethod": method.upper(),
        "description": summary,
        "type": "api",
        "parameters": (
            [
                {
                    "vendorName": "body",
                    "vendorType": "body",
                    "name": "body",
                    "type": "body",
                    "description": "body",
                    "required": True,
                    "dataType": pascal_op_id,
                    "vendorDataType": pascal_op_id,
                    "source": "request",
                    "displayName": "body",
                    "curated": False,
                    "sortOrder": 0,
                }
            ]
            if has_body
            else []
        ),
        "hooks": [],
        "standardResourceName": pascal_op_id,
        "curated": {},
        "operation": operation_to_crud(method),
        "response": {
            "contentType": "application/json",
            "contentTypeAsString": "application/json",
        },
        "createdFromTemplate": False,
    }


def build_standard_resource(path: str, method: str, op: dict) -> dict:
    op_id = op["operationId"]
    pascal_op_id = to_pascal(op_id)
    summary = op.get("summary") or op.get("x-ms-summary") or op_id
    resource_entry = build_resource_entry(path, method, op)
    return {
        "name": pascal_op_id,
        "path": path,
        "type": "standard",
        "subType": "standard",
        "elementKey": ELEMENT_KEY,
        "displayName": summary,
        "custom": "no",
        "deleted": False,
        "metadata": {
            "method": {
                method.upper(): {
                    "path": path,
                    "method": method.upper(),
                    "description": summary,
                    "operationId": op_id,
                    "operation": operation_to_crud(method),
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
        "fields": {
            "key_0": {
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
        },
        "resources": [resource_entry],
        "isPriority": False,
        "isHidden": False,
    }


def build_element_json(spec: dict, resources: list[dict]) -> dict:
    # OAuth configuration from working connector, with Snowflake-specific values
    configuration = [
        {"name": "Instance Variables", "key": "instance.variables", "description": "Instance Variables", "deleted": False, "required": False, "type": "CODE_EDITOR", "displayOrder": 100, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notification signature key", "key": "event.notification.signature.key", "description": "Event notification signature key", "deleted": False, "required": False, "type": "TEXTFIELD_128", "displayOrder": 11, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": True},
        {"name": "Base URL", "key": "base.url", "description": "Base URL", "defaultValue": "https://ACCOUNT.snowflakecomputing.com", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Client ID", "key": "oauth.api.key", "description": "OAuth API key", "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_128", "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Pagination type", "key": "pagination.type", "description": "Pagination type", "defaultValue": "page", "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Authorization URL", "key": "oauth.authorization.url", "description": "OAuth authorization URL", "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 200, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Refresh time", "key": "oauth.user.refresh_time", "description": "OAuth refresh time", "deleted": False, "required": False, "type": "TEXTFIELD_64", "displayOrder": 999, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Synchronous Bulk Notification", "key": "synchronous.bulk.notification", "description": "Enables synchronous bulk callback notification", "defaultValue": "true", "deleted": False, "required": False, "type": "BOOLEAN", "displayOrder": 100, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Pagination", "key": "pagination", "description": "Pagination", "defaultValue": "{\"defaultPageSize\":50,\"pageVendorType\":\"query\",\"maxPageSize\":100,\"minPageSize\":1,\"nextPageVendorType\":\"query\",\"pageSizeVendorType\":\"query\"}", "deleted": False, "required": False, "type": "TEXTFIELD_128", "displayOrder": 1000, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Filter null values from the response", "key": "filter.response.nulls", "description": "Used to enable/disable filtering of null values from the responses", "defaultValue": "true", "deleted": False, "required": False, "type": "BOOLEAN", "displayOrder": 99, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Basic header", "key": "oauth.basic.header", "description": "OAuth basic header", "defaultValue": "true", "deleted": False, "required": False, "type": "BOOLEAN", "displayOrder": 205, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notifications enable", "key": "event.notification.enabled", "description": "Event notifications enable", "defaultValue": "false", "deleted": False, "required": False, "type": "BOOLEAN", "displayOrder": 9, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Scope", "key": "oauth.scope", "description": "OAuth scope", "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_64", "displayOrder": 3, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Max Page Size (or limit)", "key": "pagination.max", "description": "The maximum number of records the API provider returns in a response", "defaultValue": "100", "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Access token", "key": "oauth.user.token", "description": "OAuth access token", "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 999, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Client secret", "key": "oauth.api.secret", "description": "OAuth api secret", "deleted": False, "required": False, "type": "PASSWORD", "displayOrder": 2, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Token URL", "key": "oauth.token.url", "description": "OAuth token URL", "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 201, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Token revoke URL", "key": "oauth.token.revoke_url", "description": "OAuth token revoke URL", "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 300, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Event notification basic password", "key": "event.notification.basic.password", "description": "Event notification basic password", "deleted": False, "required": False, "type": "PASSWORD", "displayOrder": 13, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": True},
        {"name": "Default select fields", "key": "default.select.fields.map", "description": "Generic map used to specify default fields for bulk download and GET /all requests.", "deleted": False, "required": False, "type": "TEXTAREA", "displayOrder": 98, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Connection Identity Lookup Key", "key": "connection.identity.lookup.key", "description": "A JSON path type string value for retrieving the connection identity.", "defaultValue": "config.connection.name", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 100, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notification basic user name", "key": "event.notification.basic.username", "description": "Event notification basic user name", "deleted": False, "required": False, "type": "TEXTFIELD_128", "displayOrder": 12, "hide": False, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notification callback headers", "key": "event.notification.callback.headers", "description": "Event notification callback headers", "deleted": False, "required": False, "type": "TEXTFIELD_128", "displayOrder": 12, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Callback URL", "key": "oauth.callback.url", "description": "OAuth callback URL", "defaultValue": "https://cloud.uipath.com/provisioning_/callback", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 200, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Authentication time", "key": "authentication.time", "description": "Time of Getting Token or Performing Authentication", "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 100, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Refresh token URL", "key": "oauth.token.refresh_url", "description": "OAuth token refresh URL", "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 202, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Refresh interval", "key": "oauth.user.refresh_interval", "description": "OAuth refresh interval", "defaultValue": "3600", "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 999, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Event poller refresh interval", "key": "event.poller.refresh_interval", "description": "Set time interval for polling vendor application (in minutes)", "defaultValue": "15", "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 101, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Refresh token", "key": "oauth.user.refresh_token", "description": "OAuth refresh token", "deleted": False, "required": False, "type": "TEXTFIELD_64", "displayOrder": 999, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Connection name", "key": "connection.name", "description": "Connection name", "defaultValue": "Snowflake REST API", "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 1000, "hide": False, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event poller resources configuration", "key": "event.poller.configuration", "description": "Event poller resources configuration", "defaultValue": "{}", "deleted": False, "required": False, "type": "TEXTAREA", "displayOrder": 14, "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
    ]

    return {
        "name": "Snowflake REST API",
        "key": ELEMENT_KEY,
        "description": "Snowflake REST API — Cortex (Analyst, Search, Inference, Embed, Agents, Threads) and SQL API. Auth: OAuth 2.0.",
        "protocolType": "http",
        "deleted": False,
        "hide": False,
        "authentication": {"type": "oauth2"},
        "configuration": configuration,
        "resources": resources,
        "parameters": [
            {"vendorName": "Content-Type", "vendorType": "header", "name": "application/json", "type": "value", "description": "The default Content-Type header"},
            {"vendorName": "Accept", "vendorType": "header", "name": "application/json", "type": "value", "description": "The default Accept header"},
        ],
        "hooks": [],
        "applicationName": "snowflakerestapi",
        "vendorName": "snowflakerestapi",
        "importSource": "SPEC",
        "pagination": {
            "minPageSize": 1,
            "maxPageSize": 200,
            "defaultPageSize": 100,
            "pageSizeVendorType": "query",
            "pageVendorType": "query",
            "nextPageVendorType": "query",
        },
        "paginatorVersion": "V3",
        "active": True,
        "beta": False,
        "bulkDownloadEnabled": False,
        "bulkUploadEnabled": False,
        "cloneable": True,
        "displayOrder": 100,
        "extendable": True,
        "extended": False,
        "hub": "general",
        "oauthRefreshTokenRefreshInterval": 0,
        "trialAccount": False,
        "typeOauth": True,
        "useModelsForMetadata": False,
        "dirty": False,
    }


def main():
    with open(SPEC_PATH) as f:
        spec = yaml.safe_load(f)

    # Collect all operations
    operations: list[tuple[str, str, dict]] = []  # (path, method, op)
    for path, path_item in spec["paths"].items():
        for method, op in path_item.items():
            if isinstance(op, dict) and "operationId" in op:
                operations.append((path, method.upper(), op))

    print(f"  Found {len(operations)} operations")

    # Build resource entries (for element.json)
    resource_entries = [build_resource_entry(path, method, op) for path, method, op in operations]

    # Build standard resource files
    standard_resources: list[tuple[str, dict]] = []
    for path, method, op in operations:
        pascal_op_id = to_pascal(op["operationId"])
        sr = build_standard_resource(path, method, op)
        standard_resources.append((f"{pascal_op_id}.json", sr))

    # Build element.json
    element = build_element_json(spec, resource_entries)

    # element-metadata.json
    element_metadata = {
        "formatVersion": "1.0.0",
        "type": "connector",
    }

    # webhook.json — null (no webhooks)
    webhook = None

    # Write zip
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "app/element/element.json",
            json.dumps(element, indent=2),
        )
        zf.writestr(
            "app/element/element-metadata.json",
            json.dumps(element_metadata, indent=2),
        )
        zf.writestr(
            "app/element/webhook.json",
            "null",
        )
        for filename, sr_data in standard_resources:
            zf.writestr(
                f"app/element/standard-resources/{filename}",
                json.dumps(sr_data, indent=2),
            )

    # Print summary
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = sorted(zf.namelist())
        size = ZIP_PATH.stat().st_size

    print(f"\nWrote {ZIP_PATH}")
    print(f"  Size: {size:,} bytes ({size // 1024} KB)")
    print(f"  Files in zip: {len(names)}")
    for n in names:
        print(f"    {n}")


if __name__ == "__main__":
    main()
