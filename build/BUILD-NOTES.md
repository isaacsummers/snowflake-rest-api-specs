# Build Notes — Snowflake Cortex REST API (UiPath)

**Output:** `build/uipath-snowflake-cortex.yaml`
**Versioned copy:** `uipath-ready/v1/snowflake-cortex-rest-api-v1.yaml`
**Builder:** `build/merge.py` (idempotent; rerun any time)

## Naming convention

Connector title format: `Snowflake Cortex REST API v<N>`
Versioned file: `uipath-ready/v<N>/snowflake-cortex-rest-api-v<N>.yaml`

When adding new endpoints for a new version:
1. Bump `info.title` to `Snowflake Cortex REST API v2` (etc.)
2. Add new paths to `KEEP_PATHS` in `merge.py`
3. Add required source specs to `PATH_FILES` / `COMMON_FILES`
4. Rebuild, validate, copy to `uipath-ready/v<N>/snowflake-cortex-rest-api-v<N>.yaml`
5. Import new version into Connector Builder as a separate connector

## v1 scope

**Paths (3):**
- `POST /api/v2/cortex/analyst/message` — Cortex Analyst send message
- `POST /api/v2/databases/{database}/schemas/{schema}/cortex-search-services/{service_name}:query` — Cortex Search query
- `POST /api/v2/databases/{database}/schemas/{schema}/cortex-search-services/{service_name}:suggest` — Cortex Search suggest

## Auth

OAuth 2.0 Authorization Code via Entra ID external OAuth integration:
- Tenant: `d73a39db-6eda-495d-8000-7579f56d68b7`
- Auth URL: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`
- Token URL: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- Scope: `session:role:DEV_FDH_PROJ_MGMT_RW`
- `X-Snowflake-Authorization-Token-Type`: `OAUTH`

## Connection-tab fields (x-ms-connection-parameter)

These appear on the auth/connection tab in UiPath Integration Service:

| Field | Header | Default |
|---|---|---|
| Snowflake Account | server variable `{account}` | `MDTPLC-AWSUSE1P1` |
| OAuth Scope | security scheme scope | `session:role:DEV_FDH_PROJ_MGMT_RW` |
| Default Warehouse | `X-Snowflake-Warehouse` | `AGENT_WH` |
| Default Database | `X-Snowflake-Database` | `DEV_FDH_DB` |
| Default Schema | `X-Snowflake-Schema` | `PROJ_MGMT` |
| Default Role | `X-Snowflake-Role` | `DEV_FDH_PROJ_MGMT_RW` |

Per-call override inputs on each activity are the same headers but blank — fill them in to override the connection default for that specific call.

## Import into UiPath Connector Builder

1. Integration Service → Connector Builder → New Connector → Import from OpenAPI
2. Upload `uipath-ready/v1/snowflake-cortex-rest-api-v1.yaml`
3. Connection setup:
   - Auth type: OAuth 2.0 Authorization Code
   - Client ID / secret: from `SNOWFLAKE_OAUTH_CREDENTIAL` Orchestrator asset
   - Callback URL: `https://cloud.uipath.com/provisioning_/callback`
   - Fill in account, warehouse, database, schema, role defaults

## Rebuilding

```bash
cd ~/projects/snowflake-rest-api-specs
uv run --with pyyaml python build/merge.py
cp build/uipath-snowflake-cortex.yaml uipath-ready/v1/snowflake-cortex-rest-api-v1.yaml
```

Validate:
```bash
uv run --with openapi-spec-validator,pyyaml python -c "
import yaml; from openapi_spec_validator import validate
validate(yaml.safe_load(open('build/uipath-snowflake-cortex.yaml')))
print('OK')"
```

## Gotchas

1. **`account` server variable** — UiPath surfaces this as a connection field. Set to `MDTPLC-AWSUSE1P1` (no `.snowflakecomputing.com` suffix).
2. **`X-Snowflake-Authorization-Token-Type`** — hardcoded `OAUTH`, sent silently, not shown as a user field.
3. **Per-call header overrides** — warehouse/database/schema/role appear on each activity as optional blank inputs. Leave blank to use connection defaults; fill in to override for that call only.
4. **Cortex Search paths have `{database}` and `{schema}` as URL path params** — these are separate from the `X-Snowflake-Database`/`X-Snowflake-Schema` headers. Both will be sent; path params are explicit per-call.
5. **No `cortex-agent` paths in v1** — hand-author `/api/v2/cortex/agent:run` against `CommonAgentRequest`/`CommonAgentResponse` schemas for a future version if needed.
