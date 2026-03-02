"""OpenAI-powered itinerary risk analysis for PREVENTION flow.

Produces contract-aligned report output with score, recommendations,
and domain-level analyst details for richer frontend display.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI

DOMAIN_PROMPTS = {
    "health_medical": "Analyze medical readiness, clinic/hospital access, disease/sanitation concerns.",
    "crime_security": "Analyze theft, assault, scam, and personal security concerns for travelers.",
    "political_civil": "Analyze protest, unrest, restrictions, and checkpoint-related concerns.",
    "environment_weather": "Analyze weather, flood, heat, terrain, and environmental hazard concerns.",
    "infrastructure": "Analyze roads, transport reliability, utilities, and communication reliability.",
}

SEVERITY_RANK = {"no": 0, "low": 1, "moderate": 2, "medium": 2, "high": 3, "severe": 4}
RANK_TO_SEVERITY = {0: "low", 1: "low", 2: "moderate", 3: "high", 4: "severe"}


class OpenAIRiskAnalyzerError(RuntimeError):
    """Raised when OpenAI-powered risk analysis cannot execute."""


def _normalize_label(value: Any, *, fallback: str = "low") -> str:
    raw = str(value or "").strip().lower()
    if raw in {"no", "none", "clear"}:
        return "low"
    if raw in {"low", "moderate", "medium", "high", "severe"}:
        return "moderate" if raw == "medium" else raw
    return fallback


def _max_label(current: str, candidate: str) -> str:
    return candidate if SEVERITY_RANK.get(candidate, 1) > SEVERITY_RANK.get(current, 1) else current


def _score_from_locations(days: list[dict[str, Any]]) -> dict[str, Any]:
    penalties = {"low": 4, "moderate": 10, "high": 18, "severe": 28}
    total_penalty = 0
    total_locations = 0

    for day in days:
        for location in day.get("locations", []):
            location_risk = _normalize_label(location.get("location_risk"), fallback="moderate")
            connectivity_risk = _normalize_label(location.get("connectivity_risk"), fallback="moderate")
            offline_minutes = int(location.get("expected_offline_minutes") or 0)

            total_penalty += penalties.get(location_risk, 10)
            total_penalty += int(penalties.get(connectivity_risk, 10) * 0.7)
            if offline_minutes >= 180:
                total_penalty += 8
            elif offline_minutes >= 90:
                total_penalty += 4
            total_locations += 1

    if total_locations == 0:
        return {
            "value": 100,
            "justification": "No itinerary locations were analyzed.",
            "details": {"total_locations": 0, "total_penalty": 0, "average_penalty": 0},
        }

    average_penalty = total_penalty / total_locations
    value = max(0, min(100, int(round(100 - average_penalty))))
    return {
        "value": value,
        "justification": "Score is based on aggregated location risk, connectivity risk, and expected offline exposure.",
        "details": {
            "total_locations": total_locations,
            "total_penalty": round(total_penalty, 2),
            "average_penalty": round(average_penalty, 2),
        },
    }


def _chat_json(client: OpenAI, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else content
        content = content.removeprefix("json").strip()
    return json.loads(content)


def _run_domain_analysis(
    *,
    client: OpenAI,
    model: str,
    itinerary: dict[str, Any],
    domain: str,
    request_id: str,
) -> dict[str, Any]:
    user_prompt = (
        f"Request id: {request_id}\n"
        f"Domain: {domain}\n"
        "Return strict JSON only in format:\n"
        "{\"items\":[{\"date\":\"YYYY-MM-DD\",\"location\":\"name\",\"risk\":\"label\","
        "\"severity\":\"low|moderate|high|severe\",\"connectivity_risk\":\"low|moderate|high|severe\","
        "\"expected_offline_minutes\":0,\"recommendation\":\"text\",\"details\":\"text\"}]}\n"
        "Use provided itinerary JSON only.\n"
        f"Itinerary:\n{json.dumps(itinerary, indent=2)}"
    )
    system_prompt = (
        "You are a Bihar travel safety analyst. Keep output concise, concrete, and actionable. "
        + DOMAIN_PROMPTS[domain]
    )
    parsed = _chat_json(client, model=model, system_prompt=system_prompt, user_prompt=user_prompt)
    items = parsed.get("items") if isinstance(parsed.get("items"), list) else []
    normalized_items: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        date = str(item.get("date") or "").strip()
        location = str(item.get("location") or "").strip()
        if not date or not location:
            continue
        normalized_items.append(
            {
                "date": date,
                "location": location,
                "risk": str(item.get("risk") or "Unspecified risk").strip(),
                "severity": _normalize_label(item.get("severity"), fallback="moderate"),
                "connectivity_risk": _normalize_label(item.get("connectivity_risk"), fallback="moderate"),
                "expected_offline_minutes": max(0, int(item.get("expected_offline_minutes") or 0)),
                "recommendation": str(item.get("recommendation") or "Review local conditions before travel.").strip(),
                "details": str(item.get("details") or "").strip(),
                "domain": domain,
            }
        )

    return {"domain": domain, "items": normalized_items}


def _aggregate_domain_results(analyst_reports: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    day_map: dict[str, dict[str, dict[str, Any]]] = {}
    recommendations: list[str] = []
    total_before = 0

    for report in analyst_reports.values():
        for item in report.get("items", []):
            if not isinstance(item, dict):
                continue
            total_before += 1
            date = item["date"]
            location_name = item["location"]

            day_locations = day_map.setdefault(date, {})
            existing = day_locations.get(location_name)
            if not existing:
                day_locations[location_name] = {
                    "name": location_name,
                    "location_risk": _normalize_label(item.get("severity"), fallback="moderate"),
                    "connectivity_risk": _normalize_label(item.get("connectivity_risk"), fallback="moderate"),
                    "expected_offline_minutes": int(item.get("expected_offline_minutes") or 0),
                }
            else:
                existing["location_risk"] = _max_label(existing["location_risk"], _normalize_label(item.get("severity"), fallback="moderate"))
                existing["connectivity_risk"] = _max_label(
                    existing["connectivity_risk"], _normalize_label(item.get("connectivity_risk"), fallback="moderate")
                )
                existing["expected_offline_minutes"] = max(
                    int(existing.get("expected_offline_minutes") or 0), int(item.get("expected_offline_minutes") or 0)
                )

            recommendation = str(item.get("recommendation") or "").strip()
            if recommendation and recommendation not in recommendations:
                recommendations.append(recommendation)

    day_entries = [
        {"date": date, "locations": list(location_map.values())}
        for date, location_map in sorted(day_map.items(), key=lambda pair: pair[0])
    ]

    total_after = sum(len(day.get("locations", [])) for day in day_entries)
    judge = {
        "applied": True,
        "before": total_before,
        "after": total_after,
        "removed": max(0, total_before - total_after),
        "error": None,
        "reason": "deduplicated_by_date_location",
    }

    return day_entries, recommendations[:8], judge


def analyze_itinerary_with_openai(itinerary: dict[str, Any], *, request_id: str, model: str | None = None) -> dict[str, Any]:
    """Run OpenAI domain analyzers and return contract-aligned risk report."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIRiskAnalyzerError("OPENAI_API_KEY is missing")

    analysis_model = model or os.getenv("ANALYZER_MODEL") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    analyst_reports: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(5, len(DOMAIN_PROMPTS))) as executor:
        future_to_domain = {
            executor.submit(
                _run_domain_analysis,
                client=client,
                model=analysis_model,
                itinerary=itinerary,
                domain=domain,
                request_id=request_id,
            ): domain
            for domain in DOMAIN_PROMPTS
        }

        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                analyst_reports[domain] = future.result()
            except Exception as exc:
                analyst_reports[domain] = {"domain": domain, "items": [], "error": str(exc)}

    days, recommendations, judge = _aggregate_domain_results(analyst_reports)
    score = _score_from_locations(days)

    summary = (
        f"Generated risk analysis for {len(days)} day(s) and {sum(len(day.get('locations', [])) for day in days)} location segment(s). "
        f"Overall score: {score['value']}."
    )

    final_report = {
        "SCORE": {"value": score["value"], "justification": score["justification"]},
        "DAY": [
            {
                "day_id": day.get("date"),
                "day_label": day.get("date"),
                "ACTIVITY": [
                    {
                        "activity": location.get("name"),
                        "location": location.get("name"),
                        "RISK": [
                            {
                                "domain": "aggregated",
                                "risk": f"Location risk {location.get('location_risk')}",
                                "severity": location.get("location_risk"),
                                "mitigation": "Follow recommendations and avoid high-risk windows.",
                                "details": f"Connectivity {location.get('connectivity_risk')}, offline up to {location.get('expected_offline_minutes')} min.",
                            }
                        ],
                    }
                    for location in day.get("locations", [])
                ],
            }
            for day in days
        ],
    }

    return {
        "report": {
            "summary": summary,
            "days": days,
            "recommendations": recommendations,
            "score": {"value": score["value"], "justification": score["justification"]},
            "score_breakdown": score,
            "judge": judge,
            "analyst_reports": analyst_reports,
            "final_report": final_report,
        }
    }
