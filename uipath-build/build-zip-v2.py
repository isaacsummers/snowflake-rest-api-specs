#!/usr/bin/env python3
"""
Build UiPath connector zip for Snowflake REST API v2.
Output: uipath-ready/v2/snowflake-rest-api-v2-connector-v2.zip
"""

import json
import re
import zipfile
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).parent.parent / "uipath-ready/v2/snowflake-rest-api-v2.yaml"
OUT_PATH = Path(__file__).parent.parent / "uipath-ready/v2/snowflake-rest-api-v2-connector-v2.zip"

CONNECTOR_KEY = "design-medtronicplc-snowflakerestapi"
BASE_HOST = "https://orgname-accountname.snowflakecomputing.com"

METHOD_TO_OPERATION = {
    "GET": "Retrieve",
    "POST": "Create",
    "PUT": "Update",
    "PATCH": "Update",
    "DELETE": "Delete",
}


def load_spec():
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)


def extract_path_params(path: str) -> list:
    return re.findall(r"\{(\w+)\}", path)


def build_resource(path, method, operation_id, summary, has_body):
    method_upper = method.upper()
    operation = METHOD_TO_OPERATION.get(method_upper, "Create")
    path_params = extract_path_params(path)

    parameters = []
    sort_order = 0

    if has_body:
        parameters.append({
            "vendorName": "body",
            "vendorType": "body",
            "name": "body",
            "type": "body",
            "description": "body",
            "required": True,
            "dataType": operation_id,
            "vendorDataType": operation_id,
            "source": "request",
            "displayName": "body",
            "curated": False,
            "sortOrder": sort_order,
        })
        sort_order += 1

    for param in path_params:
        parameters.append({
            "vendorName": param,
            "vendorType": "path",
            "name": param,
            "type": "path",
            "description": param.replace("_", " ").title(),
            "required": True,
            "dataType": "string",
            "vendorDataType": "string",
            "source": "request",
            "displayName": param.replace("_", " ").title(),
            "curated": False,
            "sortOrder": sort_order,
        })
        sort_order += 1

    return {
        "path": path,
        "vendorPath": path,
        "method": method_upper,
        "vendorMethod": method_upper,
        "description": summary,
        "type": "api",
        "parameters": parameters,
        "hooks": [],
        "standardResourceName": operation_id,
        "curated": {},
        "operation": operation,
        "response": {
            "contentType": "application/json",
            "contentTypeAsString": "application/json",
        },
        "createdFromTemplate": False,
    }


def build_standard_resource(path, method, operation_id, summary, x_ms_summary, resource):
    method_upper = method.upper()
    operation = METHOD_TO_OPERATION.get(method_upper, "Create")
    display_name = x_ms_summary if x_ms_summary else operation_id.replace("_", " ").title()

    return {
        "name": operation_id,
        "path": path,
        "type": "standard",
        "subType": "standard",
        "elementKey": CONNECTOR_KEY,
        "displayName": display_name,
        "custom": "no",
        "deleted": False,
        "metadata": {
            "method": {
                method_upper: {
                    "path": path,
                    "method": method_upper,
                    "description": summary,
                    "operationId": operation_id,
                    "operation": operation,
                }
            },
            "bulk": {
                "bulkTypes": [
                    {"direction": "DOWNLOAD", "types": ["NORMALIZED"], "operations": ["Create", "Update"]},
                    {"direction": "UPLOAD", "types": ["NORMALIZED"], "operations": ["Create", "Update"]},
                ]
            },
        },
        "fields": {
            "key_0": {
                "method": {method_upper: {"name": method_upper}},
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
        "resources": [resource],
        "isPriority": False,
        "isHidden": False,
    }


def build_element_json(resources):
    configuration = [
        {"name": "Instance Variables", "key": "instance.variables", "description": "Instance Variables",
         "deleted": False, "required": False, "type": "CODE_EDITOR", "displayOrder": 100, "hide": True,
         "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notification signature key", "key": "event.notification.signature.key",
         "description": "Event notification signature key", "deleted": False, "required": False,
         "type": "TEXTFIELD_128", "displayOrder": 11, "hide": True, "groupControl": False,
         "configLevel": "CONNECTION", "internal": False, "encrypt": True},
        {"name": "Base URL", "key": "base.url", "description": "Base URL",
         "defaultValue": BASE_HOST,
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 1,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Client ID", "key": "oauth.api.key", "description": "OAuth API key",
         "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_128",
         "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Pagination type", "key": "pagination.type", "description": "Pagination type",
         "defaultValue": "page", "deleted": False, "required": False, "type": "TEXTFIELD_32",
         "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Authorization URL", "key": "oauth.authorization.url",
         "description": "OAuth authorization URL",
         "defaultValue": BASE_HOST + "/oauth/authorize",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 200,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Refresh time", "key": "oauth.user.refresh_time", "description": "OAuth refresh time",
         "deleted": False, "required": False, "type": "TEXTFIELD_64", "displayOrder": 999,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Synchronous Bulk Notification", "key": "synchronous.bulk.notification",
         "description": "Enables synchronous bulk callback notification", "defaultValue": "true",
         "deleted": False, "required": False, "type": "BOOLEAN", "displayOrder": 100, "hide": True,
         "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Pagination", "key": "pagination", "description": "Pagination",
         "defaultValue": "{\"defaultPageSize\":50,\"pageVendorType\":\"query\",\"maxPageSize\":100,\"minPageSize\":1,\"nextPageVendorType\":\"query\",\"pageSizeVendorType\":\"query\"}",
         "deleted": False, "required": False, "type": "TEXTFIELD_128", "displayOrder": 1000,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Filter null values from the response", "key": "filter.response.nulls",
         "description": "Used to enable/disable filtering of null values from the responses",
         "defaultValue": "true", "deleted": False, "required": False, "type": "BOOLEAN",
         "displayOrder": 99, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Basic header", "key": "oauth.basic.header", "description": "OAuth basic header",
         "defaultValue": "true", "deleted": False, "required": False, "type": "BOOLEAN",
         "displayOrder": 205, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Event notifications enable", "key": "event.notification.enabled",
         "description": "Event notifications enable", "defaultValue": "false",
         "deleted": False, "required": False, "type": "BOOLEAN", "displayOrder": 9,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Scope", "key": "oauth.scope", "description": "OAuth scope",
         "defaultValue": "", "deleted": False, "required": False, "type": "TEXTFIELD_64",
         "displayOrder": 3, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Max Page Size (or limit)", "key": "pagination.max",
         "description": "The maximum number of records the API provider returns in a response",
         "defaultValue": "100", "deleted": False, "required": False, "type": "TEXTFIELD_32",
         "displayOrder": 1, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Access token", "key": "oauth.user.token", "description": "OAuth access token",
         "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 999,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Client secret", "key": "oauth.api.secret", "description": "OAuth api secret",
         "deleted": False, "required": False, "type": "PASSWORD", "displayOrder": 2,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Token URL", "key": "oauth.token.url", "description": "OAuth token URL",
         "defaultValue": BASE_HOST + "/oauth/token-request",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 201,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Token revoke URL", "key": "oauth.token.revoke_url",
         "description": "OAuth token revoke URL",
         "defaultValue": BASE_HOST + "/oauth/token-revoke",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 300,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Event notification basic password", "key": "event.notification.basic.password",
         "description": "Event notification basic password", "deleted": False, "required": False,
         "type": "PASSWORD", "displayOrder": 13, "hide": True, "groupControl": False,
         "configLevel": "CONNECTION", "internal": False, "encrypt": True},
        {"name": "Default select fields", "key": "default.select.fields.map",
         "description": "Generic map used to specify default fields for bulk download and GET /all requests. Each key should be the canonical objectName and values may be specified as a comma-delimited string or a list of strings",
         "deleted": False, "required": False, "type": "TEXTAREA", "displayOrder": 98,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Connection Identity Lookup Key", "key": "connection.identity.lookup.key",
         "description": "A JSON path type string value, possibly with dot notation. Helps to retrieve the connection identity while provisioning, then stored on element instance.  For example 'data.email' or 'email'",
         "defaultValue": "config.connection.name",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 100,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notification basic user name", "key": "event.notification.basic.username",
         "description": "Event notification basic user name", "deleted": False, "required": False,
         "type": "TEXTFIELD_128", "displayOrder": 12, "hide": False, "groupControl": False,
         "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event notification callback headers", "key": "event.notification.callback.headers",
         "description": "Event notification callback headers", "deleted": False, "required": False,
         "type": "TEXTFIELD_128", "displayOrder": 12, "hide": True, "groupControl": False,
         "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Callback URL", "key": "oauth.callback.url", "description": "OAuth callback URL",
         "defaultValue": "https://cloud.uipath.com/provisioning_/callback",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 200,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Authentication time", "key": "authentication.time",
         "description": "Time of Getting Token or Performing Authentication",
         "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 100,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Refresh token URL", "key": "oauth.token.refresh_url",
         "description": "OAuth token refresh URL",
         "defaultValue": BASE_HOST + "/oauth/token-request",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 202,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Refresh interval", "key": "oauth.user.refresh_interval",
         "description": "OAuth refresh interval", "defaultValue": "3600",
         "deleted": False, "required": False, "type": "TEXTFIELD_32", "displayOrder": 999,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Event poller refresh interval", "key": "event.poller.refresh_interval",
         "description": "Set time interval for polling vendor application (in minutes)",
         "defaultValue": "15", "deleted": False, "required": False, "type": "TEXTFIELD_32",
         "displayOrder": 101, "hide": True, "groupControl": False, "configLevel": "CONNECTION",
         "internal": False, "encrypt": False},
        {"name": "Refresh token", "key": "oauth.user.refresh_token",
         "description": "OAuth refresh token", "deleted": False, "required": False,
         "type": "TEXTFIELD_64", "displayOrder": 999, "hide": True, "groupControl": False,
         "configLevel": "CONNECTION", "internal": True, "encrypt": False},
        {"name": "Connection name", "key": "connection.name", "description": "Connection name",
         "defaultValue": "Snowflake REST API",
         "deleted": False, "required": False, "type": "TEXTFIELD_1000", "displayOrder": 1000,
         "hide": False, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
        {"name": "Event poller resources configuration", "key": "event.poller.configuration",
         "description": "Event poller resources configuration", "defaultValue": "{}",
         "deleted": False, "required": False, "type": "TEXTAREA", "displayOrder": 14,
         "hide": True, "groupControl": False, "configLevel": "CONNECTION", "internal": False, "encrypt": False},
    ]

    return {
        "name": "Snowflake REST API",
        "key": CONNECTOR_KEY,
        "description": "Snowflake REST API \u2014 Cortex (Analyst, Search, Inference, Embed, Agents, Threads) and SQL API",
        "protocolType": "http",
        "deleted": False,
        "hide": False,
        "authentication": {"type": "oauth2"},
        "configuration": configuration,
        "resources": resources,
        "parameters": [
            {"vendorName": "Content-Type", "vendorType": "header", "name": "application/json",
             "type": "value", "description": "The default Content-Type header"},
            {"vendorName": "Accept", "vendorType": "header", "name": "application/json",
             "type": "value", "description": "The default Accept header"},
        ],
        "hooks": [],
        "applicationName": "snowflakerestapi",
        "vendorName": "snowflakerestapi",
        "importSource": "BLANK",
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


def build_element_metadata():
    return {
        "name": "Snowflake REST API",
        "key": CONNECTOR_KEY,
        "description": "Snowflake REST API \u2014 Cortex (Analyst, Search, Inference, Embed, Agents, Threads) and SQL API",
        "hasCustomObjectDiscovery": False,
        "hasCustomFieldDiscovery": False,
        "hasObjectDiscovery": False,
        "hasFieldDiscovery": False,
        "hasExtensions": False,
        "hasNativeDiscovery": False,
        "vendorAPIType": "REST",
        "appName": "snowflakerestapi",
        "vendorName": "snowflakerestapi",
        "lifecycleStage": "PREVIEW",
        "discoveryType": "static",
        "tags": "custom",
        "hasEvents": False,
        "activityColor": "#E56D5C",
        "dapCompatible": True,
        "isActive": True,
        "isPrivate": True,
    }


def main():
    spec = load_spec()
    paths = spec.get("paths", {})

    resources = []
    standard_resources = {}  # operation_id -> dict

    for path, path_item in paths.items():
        for method in ["get", "post", "put", "patch", "delete"]:
            op = path_item.get(method)
            if not op:
                continue

            operation_id = op.get("operationId", "")
            summary = op.get("summary", op.get("description", ""))
            x_ms_summary = op.get("x-ms-summary", "")
            method_upper = method.upper()

            has_body = "requestBody" in op and method_upper in ("POST", "PUT", "PATCH")

            resource = build_resource(path, method_upper, operation_id, summary, has_body)
            resources.append(resource)

            sr = build_standard_resource(path, method_upper, operation_id, summary, x_ms_summary, resource)
            standard_resources[operation_id] = sr

    element = build_element_json(resources)
    element_metadata = build_element_metadata()

    base = f"{CONNECTOR_KEY}/app/element/"

    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.mkdir(f"{CONNECTOR_KEY}/")
        zf.mkdir(f"{CONNECTOR_KEY}/app/")
        zf.mkdir(f"{CONNECTOR_KEY}/app/element/")
        zf.mkdir(f"{CONNECTOR_KEY}/app/element/standard-resources/")

        zf.writestr(base + "element.json", json.dumps(element, separators=(",", ":")))
        zf.writestr(base + "element-metadata.json", json.dumps(element_metadata, indent=2))
        zf.writestr(base + "webhook.json", "null")

        for op_id, sr in standard_resources.items():
            zf.writestr(base + f"standard-resources/{op_id}.json",
                        json.dumps(sr, separators=(",", ":")))

    print(f"Written: {OUT_PATH}")
    print(f"Resources: {len(resources)}")
    print(f"Standard resources: {len(standard_resources)}")


if __name__ == "__main__":
    main()
