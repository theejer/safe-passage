import json
import math
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except Exception:
    OpenAI = None
    OPENAI_AVAILABLE = False

DEFAULT_MODEL = "gpt-5.2"
ANALYZER_MODEL = "gpt-4.1-nano"
ALLOWED_LOCATION_TYPES = {"visit", "transit", "activity"}
NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"
NEWS_HAZARD_TERMS = ["protest", "unrest", "curfew", "flood", "outbreak", "strike", '"travel advisory"']
NEWS_DOMAIN_KEYWORDS = {
    "health_medical": ["outbreak", "disease", "hospital", "medical", "sanitation", "health advisory"],
    "political_civil": ["protest", "unrest", "curfew", "election", "government", "travel advisory"],
    "environment_weather": ["flood", "storm", "cyclone", "earthquake", "landslide", "heatwave", "wildfire"],
    "infrastructure": ["strike", "transport", "airport", "rail", "road closure", "power outage", "internet outage"],
}

PARSER_SYSTEM_PROMPT = (
    "You are an itinerary parser that returns strictly valid JSON and never markdown. "
    "Extract trip, day, location, and accommodation objects with risk query metadata."
)

HEALTH_MEDICAL_SYSTEM_PROMPT = (
    "You are a Health and Medical travel risk analyst. "
    "Assess disease outbreaks, hospital and clinic availability, emergency medical access, and sanitation concerns."
)

CRIME_SECURITY_SYSTEM_PROMPT = (
    "You are a Crime and Security travel risk analyst. "
    "Assess petty theft, violent crime, scams, and terrorism-related risk for travelers."
)

POLITICAL_CIVIL_SYSTEM_PROMPT = (
    "You are a Political and Civil stability analyst. "
    "Assess protests, government instability, civil unrest, curfews, checkpoints, and travel restrictions."
)

ENVIRONMENT_WEATHER_SYSTEM_PROMPT = (
    "You are an Environment and Weather risk analyst. "
    "Assess natural disasters, extreme temperatures, seasonal hazards, and terrain-related exposure."
)

INFRASTRUCTURE_SYSTEM_PROMPT = (
    "You are an Infrastructure reliability analyst. "
    "Assess road conditions, utility/grid reliability, and internet/communications accessibility."
)

RISK_JUDGE_SYSTEM_PROMPT = (
    "You are a travel risk quality judge. "
    "Your task is to remove generic, repetitive, or low-value risk items while preserving concrete, actionable, and material risks. "
    "Return strictly valid JSON only, no markdown."
)

PARSER_OUTPUT_SCHEMA = {
    "trip": {
        "trip_id": "temp-uuid",
        "title": None,
        "start_date": None,
        "end_date": None,
        "destination_country": None,
        "home_country": None,
        "days": [
            {
                "day_id": "day-1",
                "date": None,
                "label": "Day 1",
                "day_notes": None,
                "locations": [
                    {
                        "location_id": "loc-1",
                        "type": "visit",
                        "name": None,
                        "raw_text": None,
                        "address": {"city": None, "state": None, "country": None},
                        "geo": {"lat": None, "lng": None, "source": None},
                        "time": {"start_local": None, "end_local": None, "timezone": None},
                        "transport": {"mode": None, "from_name": None, "to_name": None},
                        "risk_queries": {
                            "place_keywords": [],
                            "country_code": None,
                            "state": None,
                            "district": None,
                            "nearest_city": None,
                            "lat": None,
                            "lng": None,
                            "is_overnight": False,
                        },
                    }
                ],
                "accommodation": {
                    "accom_id": None,
                    "name": None,
                    "raw_text": None,
                    "address": {
                        "line1": None,
                        "line2": None,
                        "city": None,
                        "state": None,
                        "country": None,
                        "postal_code": None,
                    },
                    "geo": {"lat": None, "lng": None, "source": None},
                    "time": {"checkin_local": None, "checkout_local": None, "timezone": None},
                    "risk_queries": {
                        "place_keywords": [],
                        "country_code": None,
                        "state": None,
                        "district": None,
                        "nearest_city": None,
                        "lat": None,
                        "lng": None,
                        "is_overnight": True,
                    },
                },
            }
        ],
    }
}

ANALYST_OUTPUT_SCHEMA = {
    "agent": "<agent_name>",
    "domain": "<domain_name>",
    "items": [
        {
            "day_id": "day-1",
            "day_label": "Day 1",
            "activity": "<activity or location name>",
            "location": "<location or null>",
            "risk": "<short risk label>",
            "severity": "No|Low|Medium|High",
            "mitigation": "<actionable mitigation>",
            "details": "<what and why>",
        }
    ],
}

ANALYST_BACKGROUND_SCHEMA = {
    "agent": "<agent_name>",
    "domain": "<domain_name>",
    "contexts": [
        {
            "day_id": "day-1",
            "day_label": "Day 1",
            "activity": "<activity or location name>",
            "location": "<location or null>",
            "background": "<brief local context relevant to this domain>",
            "risk_drivers": ["<key driver 1>", "<key driver 2>"],
            "confidence": "Low|Medium|High",
        }
    ],
}

RISK_JUDGE_OUTPUT_SCHEMA = {
    "DAY": [
        {
            "day_id": "day-1",
            "day_label": "Day 1",
            "ACTIVITY": [
                {
                    "activity": "<activity name>",
                    "location": "<location or null>",
                    "RISK": [
                        {
                            "domain": "health_medical|crime_security|political_civil|environment_weather|infrastructure",
                            "risk": "<short risk label>",
                            "severity": "No|Low|Medium|High",
                            "mitigation": "<actionable mitigation>",
                            "details": "<what and why>",
                        }
                    ],
                }
            ],
        }
    ]
}

ANALYZER_CONFIGS = {
    "health_medical": {
        "agent": "health_medical_analyst",
        "system_prompt": HEALTH_MEDICAL_SYSTEM_PROMPT,
        "focus": "health and medical",
    },
    "crime_security": {
        "agent": "crime_security_analyst",
        "system_prompt": CRIME_SECURITY_SYSTEM_PROMPT,
        "focus": "crime and security",
    },
    "political_civil": {
        "agent": "political_civil_analyst",
        "system_prompt": POLITICAL_CIVIL_SYSTEM_PROMPT,
        "focus": "political and civil",
    },
    "environment_weather": {
        "agent": "environment_weather_analyst",
        "system_prompt": ENVIRONMENT_WEATHER_SYSTEM_PROMPT,
        "focus": "environment and weather",
    },
    "infrastructure": {
        "agent": "infrastructure_analyst",
        "system_prompt": INFRASTRUCTURE_SYSTEM_PROMPT,
        "focus": "infrastructure",
    },
}

SOLO_TRAVELER_PROFILE = {
    "traveler_type": "solo",
    "group_size": 1,
    "risk_tolerance": "moderate",
    "mobility_notes": "single person moving alone between stops",
}

_ENV_LOAD_LOCK = Lock()
_ENV_ALREADY_LOADED = False
_LOADED_ENV_FILES: list[str] = []
_OPENAI_CLIENT_LOCK = Lock()
_OPENAI_CLIENT: Any = None


def load_local_env_files(file_names: tuple[str, ...] = ("env.local", ".env.local", ".env")) -> list[str]:
    loaded_files: list[str] = []
    for file_name in file_names:
        path = Path(file_name)
        if not path.exists() or not path.is_file():
            continue

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
                value = value[1:-1]
            os.environ.setdefault(key, value)

        loaded_files.append(str(path))

    return loaded_files


def ensure_local_env_loaded(*, force_reload: bool = False) -> list[str]:
    global _ENV_ALREADY_LOADED, _LOADED_ENV_FILES

    if _ENV_ALREADY_LOADED and not force_reload:
        return list(_LOADED_ENV_FILES)

    with _ENV_LOAD_LOCK:
        if _ENV_ALREADY_LOADED and not force_reload:
            return list(_LOADED_ENV_FILES)

        _LOADED_ENV_FILES = load_local_env_files()
        _ENV_ALREADY_LOADED = True
        return list(_LOADED_ENV_FILES)


def has_openai_config() -> tuple[bool, str | None]:
    ensure_local_env_loaded()
    if not OPENAI_AVAILABLE:
        return False, "OpenAI SDK not installed. Run: pip install openai"
    if not os.getenv("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY is missing. Add it to env.local or set it in your environment."
    return True, None


def get_openai_client() -> Any:
    global _OPENAI_CLIENT

    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT

    with _OPENAI_CLIENT_LOCK:
        if _OPENAI_CLIENT is None:
            _OPENAI_CLIENT = OpenAI()
    return _OPENAI_CLIENT


def _extract_json_payload(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def _parse_json_object(raw_text: str) -> tuple[dict[str, Any] | None, str | None]:
    payload = _extract_json_payload(raw_text)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON response: {exc}"
    if not isinstance(parsed, dict):
        return None, "Model returned JSON but not an object."
    return parsed, None


def _openai_chat_json(prompt: str, *, system: str, model: str, temperature: float = 0.1) -> tuple[dict[str, Any] | None, str | None, str]:
    ok, error = has_openai_config()
    if not ok:
        return None, error, ""

    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        return None, f"OpenAI call failed: {exc}", ""

    parsed, parse_error = _parse_json_object(raw)
    return parsed, parse_error, raw


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_search_term(value: Any) -> str | None:
    text = _ntext(value)
    if not text:
        return None
    cleaned = " ".join(text.replace("\n", " ").replace("\t", " ").split())
    if len(cleaned) < 3:
        return None
    return cleaned


def _build_news_location_terms(analyzer_input: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    title = _normalize_search_term(analyzer_input.get("title"))
    if title:
        terms.append(title)

    destinations = analyzer_input.get("destination_countries") if isinstance(analyzer_input.get("destination_countries"), list) else []
    for destination in destinations:
        normalized = _normalize_search_term(destination)
        if normalized and normalized not in terms:
            terms.append(normalized)

    days = analyzer_input.get("days") if isinstance(analyzer_input.get("days"), list) else []
    for day in days:
        if not isinstance(day, dict):
            continue
        activities = day.get("activities") if isinstance(day.get("activities"), list) else []
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            location = _normalize_search_term(activity.get("location"))
            if location and location not in terms:
                terms.append(location)
            activity_name = _normalize_search_term(activity.get("activity"))
            if activity_name and activity_name not in terms and len(terms) < 10:
                terms.append(activity_name)

    return terms[:10]


def _build_news_query(analyzer_input: dict[str, Any]) -> str:
    location_terms = _build_news_location_terms(analyzer_input)
    if location_terms:
        location_clause = " OR ".join(f'"{term}"' if " " in term else term for term in location_terms)
    else:
        location_clause = "travel"

    hazard_clause = " OR ".join(NEWS_HAZARD_TERMS)
    return f"({location_clause}) AND ({hazard_clause})"


def _fetch_news_articles(analyzer_input: dict[str, Any]) -> dict[str, Any]:
    ensure_local_env_loaded()

    enabled = _as_bool(os.getenv("ENABLE_NEWS_CONTEXT"), True)
    if not enabled:
        return {"enabled": False, "articles": [], "error": None, "reason": "disabled_by_config"}

    api_key = _ntext(os.getenv("NEWS_API_KEY"))
    if not api_key:
        return {"enabled": False, "articles": [], "error": None, "reason": "missing_news_api_key"}

    query = _build_news_query(analyzer_input)
    base_url = _ntext(os.getenv("NEWS_API_BASE_URL")) or NEWS_API_BASE_URL
    page_size = max(5, min(_as_int(os.getenv("NEWS_API_PAGE_SIZE"), 20), 50))
    language = _ntext(os.getenv("NEWS_API_LANGUAGE")) or "en"
    sort_by = _ntext(os.getenv("NEWS_API_SORT_BY")) or "publishedAt"
    timeout_seconds = max(3, min(_as_int(os.getenv("NEWS_API_TIMEOUT_SECONDS"), 8), 20))
    exclude_domains = _ntext(os.getenv("NEWS_API_EXCLUDE_DOMAINS")) or "forbes.com,bloomberg.com,cointelegraph.com"

    params = {
        "q": query,
        "searchIn": "title,description",
        "language": language,
        "sortBy": sort_by,
        "pageSize": page_size,
        "excludeDomains": exclude_domains,
    }

    request_url = f"{base_url}?{urlencode(params)}"
    request = Request(
        request_url,
        headers={
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "safepassage-risk-pipeline/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"enabled": True, "articles": [], "error": f"news fetch failed: {exc}", "reason": "request_failed"}

    raw_articles = payload.get("articles") if isinstance(payload, dict) and isinstance(payload.get("articles"), list) else []
    articles: list[dict[str, Any]] = []
    for article in raw_articles:
        if not isinstance(article, dict):
            continue
        title = _ntext(article.get("title"))
        description = _ntext(article.get("description"))
        source = article.get("source") if isinstance(article.get("source"), dict) else {}
        source_name = _ntext(source.get("name"))
        published_at = _ntext(article.get("publishedAt"))
        url = _ntext(article.get("url"))
        if not title and not description:
            continue
        articles.append(
            {
                "title": title,
                "description": description,
                "source": source_name,
                "published_at": published_at,
                "url": url,
            }
        )

    return {
        "enabled": True,
        "articles": articles,
        "error": None,
        "reason": None,
        "query": query,
        "total_results": payload.get("totalResults") if isinstance(payload, dict) else None,
    }


def _article_text_blob(article: dict[str, Any]) -> str:
    parts = [
        _ntext(article.get("title")) or "",
        _ntext(article.get("description")) or "",
    ]
    return " ".join(parts).strip().lower()


def _format_article_line(article: dict[str, Any]) -> str:
    title = _ntext(article.get("title")) or "Untitled"
    source = _ntext(article.get("source")) or "unknown-source"
    published = _ntext(article.get("published_at")) or "unknown-time"
    summary = _ntext(article.get("description")) or ""
    if len(summary) > 180:
        summary = summary[:177] + "..."
    return f"- [{published}] ({source}) {title} :: {summary}".strip()


def _build_domain_news_contexts(news_payload: dict[str, Any]) -> dict[str, str]:
    articles = news_payload.get("articles") if isinstance(news_payload.get("articles"), list) else []
    if not articles:
        return {}

    per_domain_limit = max(2, min(_as_int(os.getenv("NEWS_CONTEXT_PER_DOMAIN"), 5), 8))
    contexts: dict[str, str] = {}

    for domain, keywords in NEWS_DOMAIN_KEYWORDS.items():
        selected: list[dict[str, Any]] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            blob = _article_text_blob(article)
            if any(keyword in blob for keyword in keywords):
                selected.append(article)
            if len(selected) >= per_domain_limit:
                break

        if not selected:
            continue

        lines = [
            "Recent external context from NewsAPI (treat as directional signal, verify before strong claims):"
        ]
        lines.extend(_format_article_line(article) for article in selected)
        contexts[domain] = "\n".join(lines)

    return contexts


def _ntext(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value).strip() or None


def _nfloat(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _normalize_severity(value: Any) -> str:
    raw = (_ntext(value) or "").lower()
    if raw in {"no", "none", "no risk", "no issue", "safe", "clear"}:
        return "No"
    if raw in {"high", "severe", "critical", "very high"}:
        return "High"
    if raw in {"medium", "moderate", "med"}:
        return "Medium"
    return "Low"


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _calibrate_severity(*, domain: str, risk: str | None, details: str | None, mitigation: str | None, model_severity: str) -> str:
    severity = _normalize_severity(model_severity)
    combined = " ".join([(risk or ""), (details or ""), (mitigation or "")]).lower()

    severe_harm_keywords = {
        "death",
        "fatal",
        "serious injury",
        "severe injury",
        "hospitalization",
        "kidnap",
        "abduction",
        "terror",
        "bomb",
        "armed",
        "shooting",
        "violent",
        "rape",
        "assault",
        "detention",
        "arrest",
        "war",
        "airstrike",
        "active conflict",
        "major earthquake",
        "major flood",
        "evacuation",
    }

    medium_signal_keywords = {
        "outbreak",
        "civil unrest",
        "protest",
        "strike",
        "transport disruption",
        "service outage",
        "power outage",
        "road closure",
        "scam",
        "pickpocket",
        "petty theft",
        "heat advisory",
        "heavy rain",
        "landslide",
        "access restriction",
    }

    low_signal_keywords = {
        "crowd",
        "busy area",
        "delay",
        "minor",
        "inconvenience",
        "awareness",
        "stay alert",
        "normal caution",
    }

    has_severe_harm = _contains_any(combined, severe_harm_keywords)
    has_medium_signal = _contains_any(combined, medium_signal_keywords)
    has_low_signal = _contains_any(combined, low_signal_keywords)

    if severity == "High" and not has_severe_harm:
        if domain == "crime_security" and _contains_any(combined, {"petty theft", "pickpocket", "scam"}):
            return "Medium"
        return "Medium"

    if severity == "Medium" and not has_severe_harm and not has_medium_signal and has_low_signal:
        return "Low"

    return severity


def _is_no_issue_item(risk: str | None, details: str | None, mitigation: str | None, severity: str) -> bool:
    if severity == "No":
        return True
    combined = " ".join([(risk or ""), (details or ""), (mitigation or "")]).strip().lower()
    if not combined:
        return True
    no_issue_markers = [
        "no issue",
        "no issues",
        "no risk",
        "no risks",
        "nothing significant",
        "nothing notable",
        "safe overall",
        "all clear",
    ]
    return any(marker in combined for marker in no_issue_markers)


def _normalize_location_type(value: Any, transport_mode: str | None = None) -> str:
    raw = (_ntext(value) or "").lower()
    mapping = {
        "visit": "visit",
        "stop": "visit",
        "sightseeing": "visit",
        "poi": "visit",
        "place": "visit",
        "transit": "transit",
        "travel": "transit",
        "transfer": "transit",
        "flight": "transit",
        "train": "transit",
        "bus": "transit",
        "drive": "transit",
        "activity": "activity",
        "event": "activity",
        "meal": "activity",
        "dining": "activity",
        "tour": "activity",
    }
    normalized = mapping.get(raw)
    if normalized in ALLOWED_LOCATION_TYPES:
        return normalized
    if transport_mode:
        return "transit"
    return "visit"


def _iso2(value: Any, fallback: Any = None) -> str | None:
    code = _ntext(value)
    if code and len(code) == 2 and code.isalpha():
        return code.upper()
    fb = _ntext(fallback)
    if fb and len(fb) == 2 and fb.isalpha():
        return fb.upper()
    return None


def _normalize_parser_context(raw_context: Any) -> dict[str, str | None]:
    context = raw_context if isinstance(raw_context, dict) else {}
    return {
        "trip_name": _ntext(context.get("trip_name")),
        "start_date": _ntext(context.get("start_date")),
        "end_date": _ntext(context.get("end_date")),
        "destination_country": _iso2(context.get("destination_country")),
    }


def _ensure_min_keywords(existing: Any, fallbacks: list[str]) -> list[str]:
    unique: list[str] = []
    if isinstance(existing, list):
        for item in existing:
            text = _ntext(item)
            if text and text not in unique:
                unique.append(text)

    for fallback in fallbacks:
        text = _ntext(fallback)
        if text and text not in unique:
            unique.append(text)

    fillers = ["travel safety", "local conditions", "area risk", "route disruption"]
    index = 0
    while len(unique) < 3 and index < len(fillers):
        if fillers[index] not in unique:
            unique.append(fillers[index])
        index += 1
    while len(unique) < 3:
        unique.append(f"keyword-{len(unique) + 1}")

    return unique[:8]


def _normalize_risk_queries(raw_rq: Any, *, defaults: dict[str, Any], fallback_keywords: list[str], is_overnight_default: bool) -> dict[str, Any]:
    risk_queries = raw_rq if isinstance(raw_rq, dict) else {}

    lat = _nfloat(risk_queries.get("lat"))
    lng = _nfloat(risk_queries.get("lng"))
    if lat is None:
        lat = _nfloat(defaults.get("lat"))
    if lng is None:
        lng = _nfloat(defaults.get("lng"))

    return {
        "place_keywords": _ensure_min_keywords(risk_queries.get("place_keywords"), fallback_keywords),
        "country_code": _iso2(risk_queries.get("country_code"), defaults.get("country_code")),
        "state": _ntext(risk_queries.get("state")) or _ntext(defaults.get("state")),
        "district": _ntext(risk_queries.get("district")) or _ntext(defaults.get("district")),
        "nearest_city": _ntext(risk_queries.get("nearest_city")) or _ntext(defaults.get("nearest_city")),
        "lat": lat,
        "lng": lng,
        "is_overnight": bool(risk_queries.get("is_overnight", is_overnight_default)),
    }


def normalize_parser_output(parsed: dict[str, Any], *, parser_context: dict[str, Any] | None = None) -> dict[str, Any]:
    trip = parsed.get("trip") if isinstance(parsed.get("trip"), dict) else {}
    days = trip.get("days") if isinstance(trip.get("days"), list) else []
    home_country = _iso2(trip.get("home_country"))
    normalized_context = _normalize_parser_context(parser_context)
    destination_country = normalized_context.get("destination_country") or _iso2(trip.get("destination_country"))

    normalized_days: list[dict[str, Any]] = []
    for day_index, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            continue

        day_id = _ntext(day.get("day_id")) or f"day-{day_index}"
        day_label = _ntext(day.get("label")) or f"Day {day_index}"

        locations_raw = day.get("locations") if isinstance(day.get("locations"), list) else []
        normalized_locations: list[dict[str, Any]] = []

        for loc_index, location in enumerate(locations_raw, start=1):
            if not isinstance(location, dict):
                continue

            address = location.get("address") if isinstance(location.get("address"), dict) else {}
            city = _ntext(address.get("city"))
            state = _ntext(address.get("state"))
            country = _ntext(address.get("country"))

            geo = location.get("geo") if isinstance(location.get("geo"), dict) else {}
            lat = _nfloat(geo.get("lat"))
            lng = _nfloat(geo.get("lng"))

            time_data = location.get("time") if isinstance(location.get("time"), dict) else {}
            transport = location.get("transport") if isinstance(location.get("transport"), dict) else {}
            transport_mode = _ntext(transport.get("mode"))

            location_name = _ntext(location.get("name"))
            raw_text = _ntext(location.get("raw_text"))
            location_type = _normalize_location_type(location.get("type"), transport_mode=transport_mode)

            fallback_keywords = [
                location_name or "",
                city or "",
                state or "",
                country or "",
                raw_text or "",
                transport_mode or "",
            ]

            normalized_rq = _normalize_risk_queries(
                location.get("risk_queries"),
                defaults={
                    "country_code": home_country or country,
                    "state": state,
                    "nearest_city": city,
                    "lat": lat,
                    "lng": lng,
                },
                fallback_keywords=fallback_keywords,
                is_overnight_default=False,
            )

            normalized_locations.append(
                {
                    "location_id": _ntext(location.get("location_id")) or f"loc-{day_index}-{loc_index}",
                    "type": location_type,
                    "name": location_name,
                    "raw_text": raw_text,
                    "address": {"city": city, "state": state, "country": country},
                    "geo": {"lat": lat, "lng": lng, "source": _ntext(geo.get("source"))},
                    "time": {
                        "start_local": _ntext(time_data.get("start_local")),
                        "end_local": _ntext(time_data.get("end_local")),
                        "timezone": _ntext(time_data.get("timezone")),
                    },
                    "transport": {
                        "mode": transport_mode,
                        "from_name": _ntext(transport.get("from_name")),
                        "to_name": _ntext(transport.get("to_name")),
                    },
                    "risk_queries": normalized_rq,
                }
            )

        accommodation = day.get("accommodation") if isinstance(day.get("accommodation"), dict) else {}
        acc_address = accommodation.get("address") if isinstance(accommodation.get("address"), dict) else {}
        acc_city = _ntext(acc_address.get("city"))
        acc_state = _ntext(acc_address.get("state"))
        acc_country = _ntext(acc_address.get("country"))

        acc_geo = accommodation.get("geo") if isinstance(accommodation.get("geo"), dict) else {}
        acc_lat = _nfloat(acc_geo.get("lat"))
        acc_lng = _nfloat(acc_geo.get("lng"))

        acc_time = accommodation.get("time") if isinstance(accommodation.get("time"), dict) else {}

        acc_name = _ntext(accommodation.get("name"))
        acc_raw_text = _ntext(accommodation.get("raw_text"))
        acc_keywords = [
            acc_name or "",
            acc_city or "",
            acc_state or "",
            acc_country or "",
            acc_raw_text or "",
            "hotel",
            "accommodation",
        ]

        normalized_acc_rq = _normalize_risk_queries(
            accommodation.get("risk_queries"),
            defaults={
                "country_code": home_country or acc_country,
                "state": acc_state,
                "nearest_city": acc_city,
                "lat": acc_lat,
                "lng": acc_lng,
            },
            fallback_keywords=acc_keywords,
            is_overnight_default=True,
        )

        normalized_days.append(
            {
                "day_id": day_id,
                "date": _ntext(day.get("date")),
                "label": day_label,
                "day_notes": _ntext(day.get("day_notes")),
                "locations": normalized_locations,
                "accommodation": {
                    "accom_id": _ntext(accommodation.get("accom_id")),
                    "name": acc_name,
                    "raw_text": acc_raw_text,
                    "address": {
                        "line1": _ntext(acc_address.get("line1")),
                        "line2": _ntext(acc_address.get("line2")),
                        "city": acc_city,
                        "state": acc_state,
                        "country": acc_country,
                        "postal_code": _ntext(acc_address.get("postal_code")),
                    },
                    "geo": {"lat": acc_lat, "lng": acc_lng, "source": _ntext(acc_geo.get("source"))},
                    "time": {
                        "checkin_local": _ntext(acc_time.get("checkin_local")),
                        "checkout_local": _ntext(acc_time.get("checkout_local")),
                        "timezone": _ntext(acc_time.get("timezone")),
                    },
                    "risk_queries": normalized_acc_rq,
                },
            }
        )

    return {
        "trip": {
            "trip_id": _ntext(trip.get("trip_id")) or "temp-uuid",
            "title": normalized_context.get("trip_name") or _ntext(trip.get("title")),
            "start_date": normalized_context.get("start_date") or _ntext(trip.get("start_date")),
            "end_date": normalized_context.get("end_date") or _ntext(trip.get("end_date")),
            "destination_country": destination_country,
            "home_country": home_country,
            "days": normalized_days,
        }
    }


def parser_agent(
    user_itinerary: str,
    *,
    model: str = DEFAULT_MODEL,
    request_id: str | None = None,
    parser_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_tag = request_id or "run-unknown"
    normalized_context = _normalize_parser_context(parser_context)

    context_block = ""
    if any(normalized_context.values()):
        context_block = (
            "\nForm-provided trip context (use these values directly when present):\n"
            f"{json.dumps(normalized_context, indent=2)}\n"
        )

    prompt = (
        f"Request ID: {request_tag}\n"
        "Use ONLY itinerary content enclosed between ITINERARY_START and ITINERARY_END.\n"
        "Do not use any prior or external itinerary context.\n"
        "Parse the following itinerary into strict JSON only.\n"
        "Rules:\n"
        "1) Use exact schema shape trip/days/locations/accommodation.\n"
        "2) location.type must be visit, transit, or activity.\n"
        "3) risk_queries.place_keywords must contain at least 3 useful keywords.\n"
        "4) country_code should be ISO-2 when known (e.g., IN, JP).\n"
        "5) trip.destination_country must be ISO-2 when known (e.g., JP, SG, MY).\n"
        "6) When form-provided trip context is present, use it to fill trip.title/start_date/end_date/destination_country.\n"
        "7) Unknown values should be null.\n"
        "Schema:\n"
        f"{json.dumps(PARSER_OUTPUT_SCHEMA, indent=2)}\n\n"
        f"{context_block}"
        "ITINERARY_START\n"
        f"{user_itinerary}\n"
        "ITINERARY_END"
    )
    parsed, error, raw = _openai_chat_json(prompt, system=PARSER_SYSTEM_PROMPT, model=model)
    if error:
        return {"error": error, "raw": raw}
    return normalize_parser_output(parsed or {}, parser_context=normalized_context)


def _build_activity_label(location: dict[str, Any]) -> tuple[str, str | None]:
    loc_type = _ntext(location.get("type")) or "visit"
    name = _ntext(location.get("name")) or _ntext(location.get("raw_text"))
    address = location.get("address") if isinstance(location.get("address"), dict) else {}
    city = _ntext(address.get("city"))
    state = _ntext(address.get("state"))
    country = _ntext(address.get("country"))

    if loc_type == "transit":
        transport = location.get("transport") if isinstance(location.get("transport"), dict) else {}
        mode = _ntext(transport.get("mode"))
        from_name = _ntext(transport.get("from_name"))
        to_name = _ntext(transport.get("to_name"))
        if from_name or to_name:
            activity = f"Transit: {from_name or 'origin'} to {to_name or 'destination'}"
        elif mode:
            activity = f"Transit by {mode}"
        else:
            activity = name or "Transit"
    elif loc_type == "activity":
        activity = name or "Activity"
    else:
        activity = name or "Visit"

    location_text = ", ".join([part for part in [name, city, state, country] if part]) or None
    return activity, location_text


def _build_day_activity_skeleton(parsed_itinerary: dict[str, Any]) -> list[dict[str, Any]]:
    trip = parsed_itinerary.get("trip") if isinstance(parsed_itinerary, dict) else {}
    if not isinstance(trip, dict):
        return []

    days = trip.get("days") if isinstance(trip.get("days"), list) else []
    skeleton: list[dict[str, Any]] = []

    for index, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            continue

        day_id = _ntext(day.get("day_id")) or f"day-{index}"
        day_label = _ntext(day.get("label")) or f"Day {index}"

        activities: list[dict[str, Any]] = []
        locations = day.get("locations") if isinstance(day.get("locations"), list) else []
        for location in locations:
            if not isinstance(location, dict):
                continue
            activity_name, location_text = _build_activity_label(location)
            activities.append({"activity": activity_name, "location": location_text, "RISK": []})

        accommodation = day.get("accommodation") if isinstance(day.get("accommodation"), dict) else {}
        acc_name = _ntext(accommodation.get("name")) or _ntext(accommodation.get("raw_text"))
        if acc_name:
            acc_address = accommodation.get("address") if isinstance(accommodation.get("address"), dict) else {}
            acc_location = ", ".join(
                [part for part in [acc_name, _ntext(acc_address.get("city")), _ntext(acc_address.get("country"))] if part]
            ) or None
            activities.append({"activity": f"Accommodation: {acc_name}", "location": acc_location, "RISK": []})

        if not activities:
            activities.append({"activity": "General Day Activity", "location": None, "RISK": []})

        skeleton.append({"day_id": day_id, "day_label": day_label, "ACTIVITY": activities})

    return skeleton


def _prepare_analyzer_input(parsed_itinerary: dict[str, Any]) -> dict[str, Any]:
    trip = parsed_itinerary.get("trip") if isinstance(parsed_itinerary, dict) else {}
    if not isinstance(trip, dict):
        return {"trip_id": "temp-uuid", "title": None, "days": []}

    compact_days: list[dict[str, Any]] = []
    destination_countries: list[str] = []
    destination_country = _iso2(trip.get("destination_country"))

    if destination_country and destination_country not in destination_countries:
        destination_countries.append(destination_country)

    trip_days = trip.get("days") if isinstance(trip.get("days"), list) else []
    for day in trip_days:
        if not isinstance(day, dict):
            continue
        for location in day.get("locations") if isinstance(day.get("locations"), list) else []:
            if not isinstance(location, dict):
                continue
            address = location.get("address") if isinstance(location.get("address"), dict) else {}
            country_name = _ntext(address.get("country"))
            if country_name and country_name not in destination_countries:
                destination_countries.append(country_name)

            risk_queries = location.get("risk_queries") if isinstance(location.get("risk_queries"), dict) else {}
            country_code = _ntext(risk_queries.get("country_code"))
            if country_code and country_code.upper() not in destination_countries:
                destination_countries.append(country_code.upper())
    for day in _build_day_activity_skeleton(parsed_itinerary):
        compact_days.append(
            {
                "day_id": day["day_id"],
                "day_label": day["day_label"],
                "activities": [
                    {"activity": activity.get("activity"), "location": activity.get("location")}
                    for activity in day.get("ACTIVITY", [])
                    if isinstance(activity, dict)
                ],
            }
        )

    return {
        "trip_id": _ntext(trip.get("trip_id")) or "temp-uuid",
        "title": _ntext(trip.get("title")),
        "start_date": _ntext(trip.get("start_date")),
        "end_date": _ntext(trip.get("end_date")),
        "destination_country": destination_country,
        "home_country": _ntext(trip.get("home_country")),
        "traveler_profile": SOLO_TRAVELER_PROFILE,
        "destination_countries": destination_countries,
        "days": compact_days,
    }


def analyst_agent(
    *,
    domain: str,
    parsed_itinerary: dict[str, Any],
    model: str = ANALYZER_MODEL,
    news_context: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    config = ANALYZER_CONFIGS[domain]
    request_tag = request_id or "run-unknown"
    analyzer_input = _prepare_analyzer_input(parsed_itinerary)
    home_country = _ntext(analyzer_input.get("home_country"))
    destination_countries = analyzer_input.get("destination_countries") if isinstance(analyzer_input.get("destination_countries"), list) else []

    political_context_block = ""
    if domain == "political_civil":
        political_context_block = (
            "Additional political context requirement:\n"
            f"- Traveler home_country: {home_country or 'unknown'}\n"
            f"- Destination countries/regions: {destination_countries}\n"
            "- Assess political/civil risk relative to the traveler's origin context (visa regime, consular support, "
            "state relations, restrictions applicable to foreigners, heightened scrutiny for certain passports).\n"
            "- If destination governance or access controls are unusually restrictive for foreign travelers, "
            "do not underrate severity.\n"
        )

    solo_traveler_block = (
        "Solo traveler context (always apply):\n"
        "- Assume one person traveling alone for all activities and transfers.\n"
        "- Account for solo-specific exposure: limited backup support, higher vulnerability at night/isolated areas, and single-point failure if phone, documents, or transport plans fail.\n"
        "- Prefer mitigations feasible for one person (share live location/check-ins, avoid isolated late-night routes, keep offline maps, keep emergency numbers and backup payment, choose reputable transport and lodging).\n"
    )

    solo_domain_focus = {
        "health_medical": (
            "- For solo travel, prioritize access to urgent care, language barriers in emergencies, and self-evacuation feasibility.\n"
        ),
        "crime_security": (
            "- For solo travel, emphasize lone-target risks (opportunistic theft/scams at transit hubs/nightlife) and route/time-of-day effects.\n"
        ),
        "political_civil": (
            "- For solo travel, emphasize ability to avoid unrest zones and safely reroute without local support.\n"
        ),
        "environment_weather": (
            "- For solo travel, emphasize solo navigation exposure, heat/fatigue management, and extreme-weather shelter options.\n"
        ),
        "infrastructure": (
            "- For solo travel, emphasize single-device dependency, outage resilience, and missed-connection recovery alone.\n"
        ),
    }.get(domain, "")

    severity_rubric_block = (
        "Severity rubric (use exactly one of No/Low/Medium/High):\n"
        "- No: no credible adverse signal; no special mitigation needed.\n"
        "- Low: minor inconvenience or low-consequence issues; unlikely to cause material harm; simple precautions are enough.\n"
        "- Medium: credible risk of non-trivial harm, financial loss, or safety incident requiring active mitigation and contingency planning.\n"
        "- High: credible risk of severe outcomes such as serious injury/death, violent crime, kidnapping, armed conflict exposure, unlawful detention, or major property damage/loss.\n"
        "Classification rule: prioritize potential damage/harm and crime severity over schedule disruption; if harm-impact is high, classify as High even when probability is uncertain.\n"
    )

    news_context_block = ""
    if news_context:
        news_context_block = (
            "External current-affairs context (recent headlines):\n"
            f"{news_context}\n"
            "Use this as supplementary context only; avoid overconfident conclusions when evidence is weak.\n"
        )

    background_prompt = (
        f"Request ID: {request_tag}\n"
        "Only use the provided Trip input for this request. Ignore any prior request context.\n"
        f"Build domain background context for {config['focus']} risk before any risk scoring/output.\n"
        "Return ONLY strict JSON in this schema:\n"
        f"{json.dumps(ANALYST_BACKGROUND_SCHEMA, indent=2)}\n\n"
        f"Set agent='{config['agent']}', domain='{domain}'.\n"
        "Rules:\n"
        "- Produce one context item for each day/activity when possible.\n"
        "- background should summarize local situation, traveler-relevant conditions, and practical context.\n"
        "- risk_drivers should list concise causal factors behind possible risk.\n"
        "- confidence must be Low, Medium, or High.\n"
        "- Do not output final risk items yet; this step is context only.\n"
        f"{solo_traveler_block}"
        f"{solo_domain_focus}"
        f"{political_context_block}"
        f"{news_context_block}"
        "Trip input:\n"
        f"{json.dumps(analyzer_input, indent=2)}"
    )

    background_parsed, background_error, background_raw = _openai_chat_json(
        background_prompt,
        system=config["system_prompt"],
        model=model,
        temperature=0.0,
    )

    if background_error:
        return {
            "agent": config["agent"],
            "domain": domain,
            "background_context": {"agent": config["agent"], "domain": domain, "contexts": []},
            "items": [],
            "error": f"Background context step failed: {background_error}",
            "raw": {"background": background_raw, "risk": ""},
        }

    background_context = {
        "agent": _ntext(background_parsed.get("agent")) or config["agent"],
        "domain": _ntext(background_parsed.get("domain")) or domain,
        "contexts": background_parsed.get("contexts") if isinstance(background_parsed.get("contexts"), list) else [],
    }

    prompt = (
        f"Request ID: {request_tag}\n"
        "Only use this request's Background context and Trip input. Ignore prior request context.\n"
        f"Analyze this trip for {config['focus']} risk.\n"
        "Return ONLY strict JSON in this schema:\n"
        f"{json.dumps(ANALYST_OUTPUT_SCHEMA, indent=2)}\n\n"
        f"Set agent='{config['agent']}', domain='{domain}'.\n"
        "Rules:\n"
        "- Include day_id/day_label on every item.\n"
        "- Link each risk to an activity when possible.\n"
        "- severity must be No, Low, Medium, or High.\n"
        "- Use High only for credible severe harm/violence/detention or catastrophic hazards; do not use High for routine crowding, petty theft, scams, minor delays, or normal urban caution.\n"
        "- Make outputs specific for a solo traveler (single person), including solo-specific mitigations and time/location awareness.\n"
        "- If there are no issues/risks, do not output an item for that case.\n"
        "- mitigation/details must be practical and concise.\n"
        f"{severity_rubric_block}"
        f"{solo_traveler_block}"
        f"{solo_domain_focus}"
        f"{political_context_block}"
        f"{news_context_block}"
        "You MUST use the provided background context as your first-pass research/context basis before deciding risk items.\n"
        "Background context:\n"
        f"{json.dumps(background_context, indent=2)}\n\n"
        "Trip input:\n"
        f"{json.dumps(analyzer_input, indent=2)}"
    )

    parsed, error, raw = _openai_chat_json(prompt, system=config["system_prompt"], model=model, temperature=0.0)
    if error:
        return {
            "agent": config["agent"],
            "domain": domain,
            "background_context": background_context,
            "items": [],
            "error": error,
            "raw": {"background": background_raw, "risk": raw},
        }

    items = parsed.get("items") if isinstance(parsed.get("items"), list) else []
    normalized_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        normalized_risk = _ntext(item.get("risk")) or "Unspecified risk"
        normalized_severity = _calibrate_severity(
            domain=domain,
            risk=normalized_risk,
            details=_ntext(item.get("details")),
            mitigation=_ntext(item.get("mitigation")),
            model_severity=_ntext(item.get("severity")) or "Low",
        )
        normalized_mitigation = _ntext(item.get("mitigation")) or "Use local advisories and adjust plans."
        normalized_details = _ntext(item.get("details")) or "No additional details provided."

        if _is_no_issue_item(normalized_risk, normalized_details, normalized_mitigation, normalized_severity):
            continue

        normalized_items.append(
            {
                "day_id": _ntext(item.get("day_id")),
                "day_label": _ntext(item.get("day_label")),
                "activity": _ntext(item.get("activity")),
                "location": _ntext(item.get("location")),
                "risk": normalized_risk,
                "severity": normalized_severity,
                "mitigation": normalized_mitigation,
                "details": normalized_details,
            }
        )

    return {
        "agent": _ntext(parsed.get("agent")) or config["agent"],
        "domain": _ntext(parsed.get("domain")) or domain,
        "background_context": background_context,
        "items": normalized_items,
    }


def _find_or_create_day(day_map: dict[str, dict[str, Any]], day_id: str | None, day_label: str | None) -> dict[str, Any]:
    if day_id and day_id in day_map:
        return day_map[day_id]

    if day_label:
        day_label_lower = day_label.lower()
        for existing in day_map.values():
            existing_label = (_ntext(existing.get("day_label")) or "").lower()
            if existing_label == day_label_lower:
                return existing

    if day_id:
        created = {"day_id": day_id, "day_label": day_label or day_id, "ACTIVITY": []}
        day_map[day_id] = created
        return created

    if day_map:
        first_key = next(iter(day_map))
        return day_map[first_key]

    fallback = {"day_id": "day-1", "day_label": "Day 1", "ACTIVITY": []}
    day_map["day-1"] = fallback
    return fallback


def _find_or_create_activity(day_entry: dict[str, Any], activity_name: str | None, location: str | None) -> dict[str, Any]:
    activities = day_entry.get("ACTIVITY") if isinstance(day_entry.get("ACTIVITY"), list) else []
    if day_entry.get("ACTIVITY") is not activities:
        day_entry["ACTIVITY"] = activities

    target_name = (activity_name or "General Day Activity").strip()
    target_lower = target_name.lower()

    for activity in activities:
        if not isinstance(activity, dict):
            continue
        existing_name = (_ntext(activity.get("activity")) or "").strip()
        existing_lower = existing_name.lower()
        if existing_lower == target_lower or target_lower in existing_lower or existing_lower in target_lower:
            if activity.get("location") is None and location is not None:
                activity["location"] = location
            return activity

    created = {"activity": target_name, "location": location, "RISK": []}
    activities.append(created)
    return created


def aggregate_analyzer_outputs(
    parsed_itinerary: dict[str, Any], analyst_reports: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, int], dict[str, str], dict[str, dict[str, Any]]]:
    day_list = _build_day_activity_skeleton(parsed_itinerary)
    day_map: dict[str, dict[str, Any]] = {day["day_id"]: day for day in day_list}

    day_labels: dict[str, str] = {day["day_id"]: day["day_label"] for day in day_list}

    for domain, report in analyst_reports.items():
        items = report.get("items") if isinstance(report, dict) and isinstance(report.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue

            day_id = _ntext(item.get("day_id"))
            day_label = _ntext(item.get("day_label"))
            day_entry = _find_or_create_day(day_map, day_id, day_label)

            resolved_day_id = _ntext(day_entry.get("day_id")) or "day-1"
            day_labels[resolved_day_id] = _ntext(day_entry.get("day_label")) or resolved_day_id

            severity = _normalize_severity(item.get("severity"))

            if severity == "No":
                continue

            activity_entry = _find_or_create_activity(
                day_entry,
                _ntext(item.get("activity")),
                _ntext(item.get("location")),
            )

            risks = activity_entry.get("RISK") if isinstance(activity_entry.get("RISK"), list) else []
            if activity_entry.get("RISK") is not risks:
                activity_entry["RISK"] = risks

            risk_obj = {
                "domain": domain,
                "risk": _ntext(item.get("risk")) or "Unspecified risk",
                "severity": severity,
                "mitigation": _ntext(item.get("mitigation")) or "Use local advisories and adjust plans.",
                "details": _ntext(item.get("details")) or "No additional details provided.",
            }

            dedupe_key = (
                risk_obj["domain"].lower(),
                risk_obj["risk"].lower(),
                risk_obj["severity"].lower(),
                risk_obj["mitigation"].lower(),
            )
            existing_keys = {
                (
                    (_ntext(risk.get("domain")) or "").lower(),
                    (_ntext(risk.get("risk")) or "").lower(),
                    (_ntext(risk.get("severity")) or "").lower(),
                    (_ntext(risk.get("mitigation")) or "").lower(),
                )
                for risk in risks
                if isinstance(risk, dict)
            }

            if dedupe_key not in existing_keys:
                risks.append(risk_obj)

    severity_counts = {"No": 0, "Low": 0, "Medium": 0, "High": 0}
    severity_points = {"No": 0, "Low": 2, "Medium": 6, "High": 12}
    severity_rank = {"No": 0, "Low": 1, "Medium": 2, "High": 3}
    rank_to_severity = {0: "No", 1: "Low", 2: "Medium", 3: "High"}
    domain_weights = {
        "health_medical": 1.0,
        "crime_security": 1.1,
        "political_civil": 1.4,
        "environment_weather": 1.0,
        "infrastructure": 1.0,
    }
    day_penalty: dict[str, float] = {day["day_id"]: 0.0 for day in day_list}

    final_days: list[dict[str, Any]] = []
    for day in day_map.values():
        if not isinstance(day, dict):
            continue

        day_id = _ntext(day.get("day_id")) or "day-1"
        day_penalty.setdefault(day_id, 0.0)

        activities = day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else []
        filtered_activities = []
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            risks = activity.get("RISK") if isinstance(activity.get("RISK"), list) else []
            if risks:
                domain_max_rank: dict[str, int] = {}
                for risk in risks:
                    if not isinstance(risk, dict):
                        continue
                    severity = _normalize_severity(risk.get("severity"))
                    domain = _ntext(risk.get("domain")) or ""
                    rank = severity_rank.get(severity, 1)

                    existing = domain_max_rank.get(domain)
                    if existing is None or rank > existing:
                        domain_max_rank[domain] = rank

                for domain, rank in domain_max_rank.items():
                    collapsed_severity = rank_to_severity.get(rank, "Low")
                    severity_counts[collapsed_severity] += 1
                    day_penalty[day_id] += severity_points.get(collapsed_severity, 6) * domain_weights.get(domain, 1.0)

                filtered_activities.append(activity)
        if filtered_activities:
            final_days.append(
                {
                    "day_id": day.get("day_id"),
                    "day_label": day.get("day_label"),
                    "ACTIVITY": filtered_activities,
                }
            )

    if not final_days:
        final_days = []

    final_days.sort(key=lambda day: _ntext(day.get("day_id")) or "")

    day_activity_totals: dict[str, int] = {
        (_ntext(day.get("day_id")) or "day-1"): len(day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else [])
        for day in day_list
        if isinstance(day, dict)
    }

    day_risk_stats: dict[str, dict[str, Any]] = {}
    for day_id, day in day_map.items():
        if not isinstance(day, dict):
            continue

        activities = day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else []
        high_count = 0
        medium_count = 0
        low_count = 0
        domains: set[str] = set()
        risky_activities = 0

        for activity in activities:
            if not isinstance(activity, dict):
                continue
            risks = activity.get("RISK") if isinstance(activity.get("RISK"), list) else []
            if risks:
                risky_activities += 1

            domain_max_rank: dict[str, int] = {}
            for risk in risks:
                if not isinstance(risk, dict):
                    continue
                severity = _normalize_severity(risk.get("severity"))
                domain_name = _ntext(risk.get("domain"))
                if domain_name:
                    domains.add(domain_name)
                rank = severity_rank.get(severity, 1)
                existing = domain_max_rank.get(domain_name or "")
                if existing is None or rank > existing:
                    domain_max_rank[domain_name or ""] = rank

            for rank in domain_max_rank.values():
                if rank >= 3:
                    high_count += 1
                elif rank == 2:
                    medium_count += 1
                elif rank == 1:
                    low_count += 1

        total_activities = day_activity_totals.get(day_id, 0)
        risky_activity_ratio = (risky_activities / total_activities) if total_activities > 0 else (1.0 if (high_count + medium_count + low_count) > 0 else 0.0)

        day_risk_stats[day_id] = {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total_risks": high_count + medium_count + low_count,
            "total_activities": total_activities,
            "risky_activities": risky_activities,
            "distinct_domains": len(domains),
            "risky_activity_ratio": risky_activity_ratio,
            "has_risk": (high_count + medium_count + low_count) > 0,
        }

    return final_days, day_penalty, severity_counts, day_labels, day_risk_stats


def _day_sort_key(day_id: str) -> tuple[int, str]:
    digits = "".join(ch for ch in day_id if ch.isdigit())
    if digits:
        return int(digits), day_id
    return 10**9, day_id


def _count_total_risks(day_output: list[dict[str, Any]]) -> int:
    total = 0
    for day in day_output:
        if not isinstance(day, dict):
            continue
        activities = day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else []
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            risks = activity.get("RISK") if isinstance(activity.get("RISK"), list) else []
            total += len([risk for risk in risks if isinstance(risk, dict)])
    return total


def _normalize_day_output(day_output: Any) -> list[dict[str, Any]]:
    if not isinstance(day_output, list):
        return []

    normalized_days: list[dict[str, Any]] = []
    for day in day_output:
        if not isinstance(day, dict):
            continue

        day_id = _ntext(day.get("day_id"))
        day_label = _ntext(day.get("day_label"))
        activities_raw = day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else []
        normalized_activities: list[dict[str, Any]] = []

        for activity in activities_raw:
            if not isinstance(activity, dict):
                continue

            activity_name = _ntext(activity.get("activity")) or "General Day Activity"
            location = _ntext(activity.get("location"))
            risks_raw = activity.get("RISK") if isinstance(activity.get("RISK"), list) else []
            normalized_risks: list[dict[str, Any]] = []

            for risk in risks_raw:
                if not isinstance(risk, dict):
                    continue
                normalized_severity = _normalize_severity(risk.get("severity"))
                if normalized_severity == "No":
                    continue
                normalized_risks.append(
                    {
                        "domain": _ntext(risk.get("domain")) or "infrastructure",
                        "risk": _ntext(risk.get("risk")) or "Unspecified risk",
                        "severity": normalized_severity,
                        "mitigation": _ntext(risk.get("mitigation")) or "Use local advisories and adjust plans.",
                        "details": _ntext(risk.get("details")) or "No additional details provided.",
                    }
                )

            if normalized_risks:
                normalized_activities.append(
                    {
                        "activity": activity_name,
                        "location": location,
                        "RISK": normalized_risks,
                    }
                )

        if normalized_activities:
            normalized_days.append(
                {
                    "day_id": day_id,
                    "day_label": day_label or day_id or "Unspecified Day",
                    "ACTIVITY": normalized_activities,
                }
            )

    normalized_days.sort(key=lambda day: _ntext(day.get("day_id")) or "")
    return normalized_days


def judge_collated_risks(
    day_output: list[dict[str, Any]], *, model: str = DEFAULT_MODEL, request_id: str | None = None
) -> dict[str, Any]:
    request_tag = request_id or "run-unknown"
    cleaned_input = _normalize_day_output(day_output)
    before_count = _count_total_risks(cleaned_input)
    if not cleaned_input or before_count == 0:
        return {
            "applied": False,
            "day_output": cleaned_input,
            "removed": 0,
            "before": before_count,
            "after": before_count,
            "error": None,
        }

    prompt = (
        f"Request ID: {request_tag}\n"
        "Only judge the risks provided for this request. Ignore prior request context.\n"
        "Review the collated travel risks and remove only unnecessary/generic/noisy items.\n"
        "Keep important, specific, actionable risks.\n"
        "Output STRICT JSON matching this schema:\n"
        f"{json.dumps(RISK_JUDGE_OUTPUT_SCHEMA, indent=2)}\n\n"
        "Rules:\n"
        "- Do NOT invent new risks.\n"
        "- Remove duplicates, boilerplate, and generic warnings that are normal background conditions.\n"
        "- Keep severe risks and any risk with concrete impact or concrete mitigation relevance.\n"
        "- For similar items in same activity/domain, keep only the most informative one.\n"
        "- Keep output concise but faithful to meaningful risk signal.\n"
        "Input DAY data:\n"
        f"{json.dumps(cleaned_input, indent=2)}"
    )

    judged, error, raw = _openai_chat_json(prompt, system=RISK_JUDGE_SYSTEM_PROMPT, model=model, temperature=0.0)
    if error:
        return {
            "applied": False,
            "day_output": cleaned_input,
            "removed": 0,
            "before": before_count,
            "after": before_count,
            "error": error,
            "raw": raw,
        }

    judged_days = _normalize_day_output(judged.get("DAY") if isinstance(judged, dict) else [])
    after_count = _count_total_risks(judged_days)

    if not judged_days:
        judged_days = cleaned_input
        after_count = before_count

    return {
        "applied": True,
        "day_output": judged_days,
        "removed": max(0, before_count - after_count),
        "before": before_count,
        "after": after_count,
        "error": None,
    }


def _compute_scoring_inputs_from_day_output(
    day_output: list[dict[str, Any]],
    parsed_itinerary: dict[str, Any],
    seed_day_labels: dict[str, str] | None = None,
) -> tuple[dict[str, float], dict[str, int], dict[str, str], dict[str, dict[str, Any]]]:
    day_list = _build_day_activity_skeleton(parsed_itinerary)
    day_labels: dict[str, str] = {day["day_id"]: day["day_label"] for day in day_list}
    if isinstance(seed_day_labels, dict):
        for day_id, label in seed_day_labels.items():
            day_labels[_ntext(day_id) or "day-1"] = _ntext(label) or (_ntext(day_id) or "day-1")

    severity_counts = {"No": 0, "Low": 0, "Medium": 0, "High": 0}
    severity_points = {"No": 0, "Low": 2, "Medium": 6, "High": 12}
    severity_rank = {"No": 0, "Low": 1, "Medium": 2, "High": 3}
    rank_to_severity = {0: "No", 1: "Low", 2: "Medium", 3: "High"}
    domain_weights = {
        "health_medical": 1.0,
        "crime_security": 1.1,
        "political_civil": 1.4,
        "environment_weather": 1.0,
        "infrastructure": 1.0,
    }

    day_penalty: dict[str, float] = {day["day_id"]: 0.0 for day in day_list}

    day_activity_totals: dict[str, int] = {
        (_ntext(day.get("day_id")) or "day-1"): len(day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else [])
        for day in day_list
        if isinstance(day, dict)
    }

    day_risk_stats: dict[str, dict[str, Any]] = {
        day_id: {
            "high": 0,
            "medium": 0,
            "low": 0,
            "total_risks": 0,
            "total_activities": total_activities,
            "risky_activities": 0,
            "distinct_domains": 0,
            "risky_activity_ratio": 0.0,
            "has_risk": False,
        }
        for day_id, total_activities in day_activity_totals.items()
    }

    for day in day_output:
        if not isinstance(day, dict):
            continue

        day_id = _ntext(day.get("day_id")) or "day-1"
        day_label = _ntext(day.get("day_label"))
        if day_label:
            day_labels[day_id] = day_label
        day_penalty.setdefault(day_id, 0.0)

        activities = day.get("ACTIVITY") if isinstance(day.get("ACTIVITY"), list) else []
        high_count = 0
        medium_count = 0
        low_count = 0
        risky_activities = 0
        domains: set[str] = set()

        for activity in activities:
            if not isinstance(activity, dict):
                continue
            risks = activity.get("RISK") if isinstance(activity.get("RISK"), list) else []
            if not risks:
                continue

            risky_activities += 1
            domain_max_rank: dict[str, int] = {}

            for risk in risks:
                if not isinstance(risk, dict):
                    continue
                severity = _normalize_severity(risk.get("severity"))
                if severity == "No":
                    continue
                domain = _ntext(risk.get("domain")) or "infrastructure"
                domains.add(domain)
                rank = severity_rank.get(severity, 1)
                existing = domain_max_rank.get(domain)
                if existing is None or rank > existing:
                    domain_max_rank[domain] = rank

            for domain, rank in domain_max_rank.items():
                collapsed_severity = rank_to_severity.get(rank, "Low")
                severity_counts[collapsed_severity] += 1
                day_penalty[day_id] += severity_points.get(collapsed_severity, 6) * domain_weights.get(domain, 1.0)

                if rank >= 3:
                    high_count += 1
                elif rank == 2:
                    medium_count += 1
                elif rank == 1:
                    low_count += 1

        total_activities = day_activity_totals.get(day_id, len(activities))
        total_risks = high_count + medium_count + low_count
        risky_activity_ratio = (risky_activities / total_activities) if total_activities > 0 else (1.0 if total_risks > 0 else 0.0)

        day_risk_stats[day_id] = {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total_risks": total_risks,
            "total_activities": total_activities,
            "risky_activities": risky_activities,
            "distinct_domains": len(domains),
            "risky_activity_ratio": risky_activity_ratio,
            "has_risk": total_risks > 0,
        }

    return day_penalty, severity_counts, day_labels, day_risk_stats


def _should_run_risk_judge(day_output: list[dict[str, Any]], severity_counts: dict[str, int]) -> bool:
    total_risks = _count_total_risks(day_output)
    if total_risks < 10:
        return False

    low = int(severity_counts.get("Low", 0) or 0)
    medium = int(severity_counts.get("Medium", 0) or 0)
    high = int(severity_counts.get("High", 0) or 0)
    low_ratio = (low / total_risks) if total_risks > 0 else 0.0

    if high > 0:
        return True
    if low >= 20:
        return True
    if (low + medium) >= 25:
        return True
    if low_ratio >= 0.55:
        return True
    return False


def compute_algorithmic_score(
    day_penalty: dict[str, float],
    severity_counts: dict[str, int],
    day_labels: dict[str, str],
    day_risk_stats: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not day_penalty:
        return {
            "value": 100,
            "justification": "No analyzer risks were produced; default score is 100.",
            "day_scores": {},
            "details": {},
        }

    day_scores: dict[str, int] = {}
    day_component_details: dict[str, dict[str, Any]] = {}

    for day_id, penalty in day_penalty.items():
        stats = day_risk_stats.get(day_id, {}) if isinstance(day_risk_stats.get(day_id), dict) else {}
        high_count = int(stats.get("high", 0) or 0)
        medium_count = int(stats.get("medium", 0) or 0)
        low_count = int(stats.get("low", 0) or 0)
        total_risks = int(stats.get("total_risks", high_count + medium_count + low_count) or 0)
        total_activities = int(stats.get("total_activities", 0) or 0)
        distinct_domains = int(stats.get("distinct_domains", 0) or 0)
        risky_activity_ratio = float(stats.get("risky_activity_ratio", 0.0) or 0.0)

        activity_scale = 1.0 + (0.45 * math.log1p(max(0, total_activities - 1)))
        risk_scale = 1.0 + (0.30 * math.log1p(max(0, total_risks - 1)))
        normalized_input = max(0.0, penalty) / (activity_scale * risk_scale)

        pressure = 1.0 - math.exp(-normalized_input / 24.0)
        normalized_penalty = 72.0 * pressure

        high_ratio = (high_count / total_risks) if total_risks > 0 else 0.0
        medium_ratio = (medium_count / total_risks) if total_risks > 0 else 0.0

        severity_shock = 0.0
        if high_count > 0:
            severity_shock += 12.0 + min(14.0, 4.0 * (high_count - 1))
            if high_ratio >= 0.4:
                severity_shock += 2.0
        if medium_count >= 4 and medium_ratio >= 0.3:
            severity_shock += 3.0
        if medium_count >= 7 and medium_ratio >= 0.45:
            severity_shock += 2.0
        if low_count >= 10 and high_count == 0 and medium_count == 0:
            severity_shock += 1.0

        spread_shock = min(5.0, max(0, distinct_domains - 1) * 1.2)
        exposure_shock = 4.0 * min(1.0, max(0.0, risky_activity_ratio))

        total_day_penalty = normalized_penalty + severity_shock + spread_shock + exposure_shock
        score = int(round(100 - total_day_penalty))
        if score < 0:
            score = 0
        if score > 100:
            score = 100

        if high_count == 0:
            score = max(score, 40)
            if medium_count <= 2:
                score = max(score, 55)

        day_scores[day_id] = score
        day_component_details[day_id] = {
            "raw_penalty": round(float(penalty), 3),
            "normalized_input": round(normalized_input, 3),
            "activity_scale": round(activity_scale, 3),
            "risk_scale": round(risk_scale, 3),
            "normalized_penalty": round(normalized_penalty, 3),
            "severity_shock": round(severity_shock, 3),
            "spread_shock": round(spread_shock, 3),
            "exposure_shock": round(exposure_shock, 3),
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total_risks": total_risks,
            "total_activities": total_activities,
            "distinct_domains": distinct_domains,
            "risky_activity_ratio": round(risky_activity_ratio, 3),
        }

    ordered_days = sorted(day_scores.keys(), key=_day_sort_key)
    ordered_scores = [day_scores[day_id] for day_id in ordered_days]

    mean_score = sum(ordered_scores) / max(1, len(ordered_scores))
    worst_day_id = min(day_scores, key=day_scores.get)
    worst_day_score = day_scores[worst_day_id]
    tail_count = min(2, len(ordered_scores))
    tail_average = sum(sorted(ordered_scores)[:tail_count]) / max(1, tail_count)

    overall = int(round((0.60 * mean_score) + (0.25 * tail_average) + (0.15 * worst_day_score)))

    single_day_shock = 0
    if len(ordered_scores) > 1:
        median_like = sorted(ordered_scores)[len(ordered_scores) // 2]
        gap = max(0, int(round(median_like - worst_day_score)))
        if gap >= 30:
            single_day_shock = min(8, 2 + (gap - 30) // 6)

    high_risk_day_ids = [day_id for day_id, detail in day_component_details.items() if int(detail.get("high", 0) or 0) > 0]
    high_risk_day_ratio = (len(high_risk_day_ids) / len(ordered_days)) if ordered_days else 0.0
    high_risk_day_penalty = int(round(10 * high_risk_day_ratio))

    longest_risky_streak = 0
    current_streak = 0
    for day_id in ordered_days:
        day_score = day_scores[day_id]
        is_risky = day_score < 50
        if is_risky:
            current_streak += 1
            if current_streak > longest_risky_streak:
                longest_risky_streak = current_streak
        else:
            current_streak = 0

    streak_penalty = 0
    if longest_risky_streak >= 2:
        streak_ratio = (longest_risky_streak / len(ordered_days)) if ordered_days else 0.0
        streak_penalty = min(8, int(round((2 + ((longest_risky_streak - 2) * 2)) * streak_ratio)))

    overall -= single_day_shock
    overall -= high_risk_day_penalty
    overall -= streak_penalty

    if overall < 0:
        overall = 0
    if overall > 100:
        overall = 100

    total_scored_risks = (
        int(severity_counts.get("High", 0))
        + int(severity_counts.get("Medium", 0))
        + int(severity_counts.get("Low", 0))
    )
    low_dominant_uplift = 0
    no_high_floor = 0

    if severity_counts.get("High", 0) == 0:
        no_high_floor = 58
        overall = max(overall, no_high_floor)

        if total_scored_risks > 0:
            medium_ratio_global = int(severity_counts.get("Medium", 0)) / total_scored_risks
            low_ratio_global = int(severity_counts.get("Low", 0)) / total_scored_risks

            if medium_ratio_global <= 0.35 and low_ratio_global >= 0.55:
                low_dominant_uplift = min(12, int(round((0.35 - medium_ratio_global) * 30)) + 4)
            elif medium_ratio_global <= 0.50 and low_ratio_global >= 0.45:
                low_dominant_uplift = min(6, int(round((0.50 - medium_ratio_global) * 16)) + 2)

        overall = min(100, overall + low_dominant_uplift)

    worst_day_id = min(day_scores, key=day_scores.get)
    worst_day_label = day_labels.get(worst_day_id, worst_day_id)

    justification = (
        f"Risk score uses nonlinear day pressure, severity/domain spread, and exposure concentration, "
        f"with worst-day and lower-tail weighting. Observed {severity_counts.get('High', 0)} high, "
        f"{severity_counts.get('Medium', 0)} medium, and {severity_counts.get('Low', 0)} low risks. "
        f"Lowest day score occurs on {worst_day_label}, and worst-day/edge-case shock penalties were applied where relevant."
    )

    return {
        "value": overall,
        "justification": justification,
        "day_scores": day_scores,
        "details": {
            "day_components": day_component_details,
            "mean_score": round(mean_score, 2),
            "tail_average": round(tail_average, 2),
            "worst_day_score": worst_day_score,
            "single_day_shock": single_day_shock,
            "high_risk_day_ratio": round(high_risk_day_ratio, 3),
            "high_risk_day_penalty": high_risk_day_penalty,
            "longest_risky_streak": longest_risky_streak,
            "streak_penalty": streak_penalty,
            "no_high_floor": no_high_floor,
            "low_dominant_uplift": low_dominant_uplift,
        },
    }


def run_itinerary_pipeline(
    user_itinerary: str,
    *,
    model: str = DEFAULT_MODEL,
    analyzer_model: str = ANALYZER_MODEL,
    parser_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    itinerary_text = (user_itinerary or "").strip()
    if not itinerary_text:
        return {"status": "failed", "stage": "input", "details": {"error": "Itinerary text is empty."}}

    request_id = f"run-{uuid.uuid4().hex[:12]}"

    ok, error = has_openai_config()
    if not ok:
        return {"status": "failed", "stage": "config", "details": {"error": error}}

    parsed = parser_agent(
        itinerary_text,
        model=model,
        request_id=request_id,
        parser_context=parser_context,
    )
    if "error" in parsed:
        return {"status": "failed", "stage": "parser", "details": parsed}

    domains = list(ANALYZER_CONFIGS.keys())
    analyst_reports: dict[str, dict[str, Any]] = {}

    analyzer_input = _prepare_analyzer_input(parsed)
    news_payload = _fetch_news_articles(analyzer_input)
    domain_news_context = _build_domain_news_contexts(news_payload)

    with ThreadPoolExecutor(max_workers=min(5, len(domains))) as executor:
        future_to_domain = {
            executor.submit(
                analyst_agent,
                domain=domain,
                parsed_itinerary=parsed,
                model=analyzer_model,
                news_context=domain_news_context.get(domain),
                request_id=request_id,
            ): domain
            for domain in domains
        }

        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                analyst_reports[domain] = future.result()
            except Exception as exc:
                analyst_reports[domain] = {
                    "agent": ANALYZER_CONFIGS[domain]["agent"],
                    "domain": domain,
                    "items": [],
                    "error": f"Analyzer failed: {exc}",
                }

    analyst_reports = {
        domain: analyst_reports.get(
            domain,
            {
                "agent": ANALYZER_CONFIGS[domain]["agent"],
                "domain": domain,
                "items": [],
                "error": "Analyzer failed: no result produced.",
            },
        )
        for domain in domains
    }

    day_output, day_penalty, severity_counts, day_labels, day_risk_stats = aggregate_analyzer_outputs(parsed, analyst_reports)

    judge_result: dict[str, Any]
    if _should_run_risk_judge(day_output, severity_counts):
        judge_result = judge_collated_risks(day_output, model=analyzer_model, request_id=request_id)
    else:
        before = _count_total_risks(day_output)
        judge_result = {
            "applied": False,
            "day_output": day_output,
            "removed": 0,
            "before": before,
            "after": before,
            "error": None,
            "reason": "skipped_by_policy",
        }

    if judge_result.get("applied") and isinstance(judge_result.get("day_output"), list):
        day_output = judge_result.get("day_output", day_output)
        day_penalty, severity_counts, day_labels, day_risk_stats = _compute_scoring_inputs_from_day_output(
            day_output,
            parsed,
            seed_day_labels=day_labels,
        )

    score_data = compute_algorithmic_score(day_penalty, severity_counts, day_labels, day_risk_stats)

    final_report = {
        "SCORE": {
            "value": int(score_data.get("value", 100)),
            "justification": str(score_data.get("justification", "")),
        },
        "DAY": day_output,
    }

    return {
        "status": "ok",
        "parsed_itinerary": parsed,
        "analyst_reports": analyst_reports,
        "news_context": {
            "enabled": bool(news_payload.get("enabled")),
            "reason": news_payload.get("reason"),
            "error": news_payload.get("error"),
            "query": news_payload.get("query"),
            "article_count": len(news_payload.get("articles") if isinstance(news_payload.get("articles"), list) else []),
            "domain_contexts": sorted(list(domain_news_context.keys())),
        },
        "judge": {
            "applied": bool(judge_result.get("applied")),
            "before": int(judge_result.get("before", 0) or 0),
            "after": int(judge_result.get("after", 0) or 0),
            "removed": int(judge_result.get("removed", 0) or 0),
            "error": judge_result.get("error"),
            "reason": judge_result.get("reason"),
        },
        "final_report": final_report,
        "score_breakdown": score_data,
    }


if __name__ == "__main__":
    loaded = ensure_local_env_loaded()
    if loaded:
        print(f"Loaded environment file(s): {', '.join(loaded)}")

    config_ok, config_error = has_openai_config()
    if not config_ok:
        print(f"Configuration error: {config_error}")
        print("Add OPENAI_API_KEY to env.local and retry.")
        raise SystemExit(1)

    sample_itinerary = "\n".join(
        [
            "Trip to Japan from 2026-05-03 to 2026-05-05.",
            "Day 1: Arrive in Tokyo, Shibuya crossing walk, dinner in Shinjuku, hotel in Shinjuku.",
            "Day 2: Asakusa temple, Ueno park, Akihabara evening.",
            "Day 3: Tsukiji market, teamLab, Ginza shopping, late dinner in Roppongi.",
        ]
    )

    print("--- Running parser + 5 analyzers pipeline ---")
    output = run_itinerary_pipeline(sample_itinerary, model=DEFAULT_MODEL, analyzer_model=ANALYZER_MODEL)
    print("Status:", output.get("status"))
    if output.get("status") != "ok":
        print(json.dumps(output, indent=2))
    else:
        print(json.dumps(output["final_report"], indent=2))
