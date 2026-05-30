# UiPath Integration Service Connector — Snowflake REST API

Pre-built UiPath connector packages for the Snowflake REST API (Cortex, SQL, Agents, Search).

## Published version

**v4** — `v2/snowflake-rest-api-v2-connector-v4.zip`

### What's included
- 34 activities covering Cortex Agents, Analyst, Inference, OpenAI/Anthropic format, Embed, Search, SQL, and Threads
- 31/34 activities with fully curated request + response fields
- OAuth 2.0 connection with 4 required fields: Account Identifier, Client ID, Client Secret, Scope
- All URLs use `{orgname-accountname}` variable interpolation

### Connection setup
| Field | Description | Example |
|---|---|---|
| Snowflake Account Identifier | orgname-accountname format | `myorg-myaccount` |
| Client ID | OAuth security integration Client ID | — |
| Client Secret | OAuth security integration Client Secret | — |
| Scope | Snowflake role scope | `session:role:MY_ROLE_NAME` |

## Version history
- **v4** — Full field curation (request + response), all connection hints, curated activity display names
- **v3** — Real field names on 11 key activities, connection hints added
- **v2** — Initial working connector (orgname-accountname path fix, OAuth URLs)

## Build scripts
See `../build/` for the Python build scripts used to generate each version.

## Updating from upstream
\`\`\`bash
git fetch upstream
git merge upstream/main
\`\`\`
