# Published UiPath Connector Releases

These are the connector packages as downloaded from UiPath after publishing.

| File | UiPath Version | Content |
|---|---|---|
| `snowflake-rest-api-uipath-v1.2.0.zip` | 1.2.0 | 37 activities — full Threads API, Cortex Analyst with semantic_view/semantic_models, curated fields |
| `snowflake-rest-api-uipath-v1.0.0.zip` | 1.0.0 | 34 activities — initial published release |

## Version notes

### 1.2.0
- Added UpdateThread, ListThreads, DeleteThread
- Fixed DescribeThread pagination params (page_size, last_message_id)
- CortexAnalyst: added semantic_view and semantic_models fields, fixed semantic_model type
- Full request + response field curation across all 31 curated activities

### 1.0.0
- Initial published release
