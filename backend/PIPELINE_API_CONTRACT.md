# Travel Risk Pipeline Contract (Integrated Backend)

## Endpoint
- **Method**: `POST`
- **Path**: `/itinerary/analyze-pipeline`
- **Content-Type**: `application/json`

## Canonical Contract Files
- Request schema: `../contracts/api/prevention/pipeline_analyze.request.json`
- Response schema: `../contracts/api/prevention/pipeline_analyze.response.json`

## Runtime Implementation
- Route: `app/routes/itinerary_analysis.py` (`analyze_pipeline_route`)
- Adapter: `app/services/pipeline_adapter.py`
- Pipeline engine: `app/services/pipeline_backend.py`

## Behavior Notes
- Returns HTTP 200 for both success and deterministic pipeline failure payloads.
- `trip_id` is optional; when provided, backend attempts to persist `final_report` and returns a `saved` object.
- `parser_model` and `analyzer_model` are optional and default to backend-configured model constants.
- Optional parser hints are supported from form inputs: `trip_name`, `start_date`, `end_date`, and `destination_country`.
- `destination_country` is normalized as ISO-2 (e.g., `JP`, `SG`, `MY`) before parser output is finalized.
