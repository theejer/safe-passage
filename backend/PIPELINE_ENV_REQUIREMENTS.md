# Environment and Runtime Requirements

## Required
- `OPENAI_API_KEY` must be set (or provided through `env.local`).

## News Context (Optional)
- `NEWS_API_KEY` for NewsAPI enrichment (`X-Api-Key` request header).
- `ENABLE_NEWS_CONTEXT=true|false` (default: true)
- `NEWS_API_BASE_URL` (default: `https://newsapi.org/v2/everything`)
- `NEWS_API_PAGE_SIZE` (default: 20, max: 50)
- `NEWS_API_TIMEOUT_SECONDS` (default: 8)
- `NEWS_API_LANGUAGE` (default: `en`)
- `NEWS_API_SORT_BY` (default: `publishedAt`)
- `NEWS_API_EXCLUDE_DOMAINS` (default: `forbes.com,bloomberg.com,cointelegraph.com`)
- `NEWS_CONTEXT_PER_DOMAIN` (default: 5)

## Optional
- `parser_model` in request payload (defaults to `DEFAULT_MODEL` in `app/services/pipeline_backend.py`).
- `analyzer_model` in request payload (defaults to `ANALYZER_MODEL` in `app/services/pipeline_backend.py`).

## Python Setup
1. Create venv
2. Install dependencies from `requirements.txt`
3. Ensure backend import works:
   - `from app.services.pipeline_backend import run_itinerary_pipeline`

## API Entry Point
- Integrated route: `POST /itinerary/analyze-pipeline`
- Route module: `app/routes/itinerary_analysis.py`

## Service Behavior Notes
- Analyzer domains run in parallel.
- Local env file is loaded once and cached in-process.
- OpenAI client is reused in-process for speed.
- Risk judge call is adaptive (may be skipped when noise level is low).

## Suggested API Operational Defaults
- Request timeout: 120s
- Retry policy: no automatic retries on parser/analyst semantic failures
- Concurrency: 1-4 workers initially (depends on OpenAI rate limits)
