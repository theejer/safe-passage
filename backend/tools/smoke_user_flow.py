"""Simple end-to-end smoke runner for SafePassage backend.

Simulates a core user flow against a running backend and verifies persistence
in the configured database.

Flow:
1) health check
2) create user
3) fetch user
4) create trip
5) list trips by user
6) upsert itinerary
7) fetch itinerary
8) optional heartbeat check (auth-enforced or demo-fallback)
9) direct DB verification of inserted rows

Usage examples:
    python tools/smoke_user_flow.py
    python tools/smoke_user_flow.py --base-url http://127.0.0.1:5000 --heartbeat-check auth
    python tools/smoke_user_flow.py --heartbeat-check demo --cleanup
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".env.local", override=True)


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str
    duration_ms: int


def _iso_today(offset_days: int = 0) -> str:
    return (date.today() + timedelta(days=offset_days)).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_step(name: str, fn) -> StepResult:
    started = time.perf_counter()
    try:
        detail = fn()
        duration_ms = int((time.perf_counter() - started) * 1000)
        return StepResult(name=name, ok=True, detail=str(detail), duration_ms=duration_ms)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return StepResult(name=name, ok=False, detail=str(exc), duration_ms=duration_ms)


def _request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    expected_status: int | tuple[int, ...],
    payload: dict | None = None,
) -> tuple[int, object | None, str]:
    response = session.request(method=method, url=url, json=payload, timeout=20)
    if isinstance(expected_status, int):
        expected = (expected_status,)
    else:
        expected = expected_status

    content_type = response.headers.get("content-type", "")
    as_text = response.text
    parsed: object | None = None
    if "application/json" in content_type and as_text:
        try:
            parsed = response.json()
        except Exception:
            parsed = None

    if response.status_code not in expected:
        raise RuntimeError(
            f"{method} {url} expected {expected} but got {response.status_code}. "
            f"Body: {as_text[:400]}"
        )

    return response.status_code, parsed, as_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run backend+DB smoke flow.")
    parser.add_argument("--base-url", default=os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--db-url", default=os.getenv("SQLALCHEMY_DATABASE_URI", "").strip())
    parser.add_argument(
        "--heartbeat-check",
        choices=("off", "auto", "auth", "demo"),
        default="auto",
        help="off=skip; auth=expect 401; demo=expect 204; auto=accept either auth-enforced or demo fallback",
    )
    parser.add_argument("--skip-db", action="store_true", help="Skip direct DB verification")
    parser.add_argument("--cleanup", action="store_true", help="Delete inserted smoke rows after run")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    base_url = args.base_url.rstrip("/")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    smoke_user_id = str(uuid4())
    smoke_trip_id = str(uuid4())
    trip_title = f"Smoke Trip {datetime.now().strftime('%H%M%S')}"

    user_payload = {
        "id": smoke_user_id,
        "full_name": "Smoke Tester",
        "phone": "+919100000001",
        "emergency_contact": {
            "name": "Smoke Contact",
            "phone": "+919100000002",
        },
    }
    trip_payload = {
        "id": smoke_trip_id,
        "user_id": smoke_user_id,
        "title": trip_title,
        "trip_planned": True,
        "start_date": _iso_today(0),
        "end_date": _iso_today(2),
        "heartbeat_enabled": True,
    }
    itinerary_payload = {
        "days": [
            {
                "date": _iso_today(0),
                "locations": [
                    {
                        "name": "Patna Junction",
                        "district": "Patna",
                        "block": "Patna Sadar",
                        "connectivity_zone": "medium",
                        "assumed_location_risk": "low",
                    }
                ],
                "accommodation": "Test Lodge",
            }
        ],
        "meta": {"source": "smoke-script", "generated_at": _now_iso()},
    }

    created_user: dict | None = None
    created_trip: dict | None = None

    results: list[StepResult] = []

    results.append(
        _run_step(
            "health",
            lambda: _request_json(session, "GET", f"{base_url}/health", expected_status=200)[0],
        )
    )

    def _create_user() -> str:
        nonlocal created_user
        _, parsed, _ = _request_json(
            session,
            "POST",
            f"{base_url}/api/users",
            expected_status=201,
            payload=user_payload,
        )
        if not isinstance(parsed, dict) or parsed.get("id") != smoke_user_id:
            raise RuntimeError(f"Unexpected user create response: {parsed}")
        created_user = parsed
        return f"created user_id={parsed.get('id')}"

    results.append(_run_step("create_user", _create_user))

    results.append(
        _run_step(
            "get_user",
            lambda: _request_json(
                session,
                "GET",
                f"{base_url}/api/users/{smoke_user_id}",
                expected_status=200,
            )[0],
        )
    )

    def _create_trip() -> str:
        nonlocal created_trip
        _, parsed, _ = _request_json(
            session,
            "POST",
            f"{base_url}/api/trips",
            expected_status=201,
            payload=trip_payload,
        )
        if not isinstance(parsed, dict) or parsed.get("id") != smoke_trip_id:
            raise RuntimeError(f"Unexpected trip create response: {parsed}")
        created_trip = parsed
        return f"created trip_id={parsed.get('id')}"

    results.append(_run_step("create_trip", _create_trip))

    def _list_trips() -> str:
        _, parsed, _ = _request_json(
            session,
            "GET",
            f"{base_url}/api/trips?user_id={smoke_user_id}",
            expected_status=200,
        )
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Unexpected trips response: {parsed}")
        items = parsed.get("items")
        if not isinstance(items, list):
            raise RuntimeError(f"Missing items array: {parsed}")
        if smoke_trip_id not in [str(item.get("id")) for item in items if isinstance(item, dict)]:
            raise RuntimeError("Created trip not found in list response")
        return f"items={len(items)}"

    results.append(_run_step("list_trips", _list_trips))

    results.append(
        _run_step(
            "upsert_itinerary",
            lambda: _request_json(
                session,
                "PUT",
                f"{base_url}/api/trips/{smoke_trip_id}/itinerary",
                expected_status=200,
                payload=itinerary_payload,
            )[0],
        )
    )

    def _get_itinerary() -> str:
        _, parsed, _ = _request_json(
            session,
            "GET",
            f"{base_url}/api/trips/{smoke_trip_id}/itinerary",
            expected_status=200,
        )
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Unexpected itinerary response: {parsed}")
        if str(parsed.get("trip_id")) != smoke_trip_id:
            raise RuntimeError(f"Itinerary trip_id mismatch: {parsed.get('trip_id')}")
        return "itinerary fetched"

    results.append(_run_step("get_itinerary", _get_itinerary))

    if args.heartbeat_check != "off":
        heartbeat_payload = {
            "user_id": smoke_user_id,
            "trip_id": smoke_trip_id,
            "timestamp": _now_iso(),
            "network_status": "online",
            "source": "manual_debug",
        }

        def _heartbeat() -> str:
            expected: int | tuple[int, ...]
            if args.heartbeat_check == "auth":
                expected = 401
            elif args.heartbeat_check == "demo":
                expected = 204
            else:
                expected = (204, 401)

            status, _, body_text = _request_json(
                session,
                "POST",
                f"{base_url}/heartbeat",
                expected_status=expected,
                payload=heartbeat_payload,
            )
            if status == 401:
                return "auth enforced (401)"
            return "ingest accepted (204)"

        results.append(_run_step("heartbeat_check", _heartbeat))

    engine = None
    if not args.skip_db:
        if not args.db_url:
            results.append(
                StepResult(
                    name="db_verify",
                    ok=False,
                    detail="Missing DB URL. Pass --db-url or set SQLALCHEMY_DATABASE_URI.",
                    duration_ms=0,
                )
            )
        else:
            engine = create_engine(args.db_url, pool_pre_ping=True)

            def _db_verify() -> str:
                with engine.begin() as conn:
                    user_found = conn.execute(
                        text("SELECT id FROM users WHERE id = :id LIMIT 1"),
                        {"id": smoke_user_id},
                    ).scalar_one_or_none()
                    if not user_found:
                        raise RuntimeError("users row not found")

                    trip_found = conn.execute(
                        text("SELECT id FROM trips WHERE id = :id AND user_id = :user_id LIMIT 1"),
                        {"id": smoke_trip_id, "user_id": smoke_user_id},
                    ).scalar_one_or_none()
                    if not trip_found:
                        raise RuntimeError("trips row not found")

                    itinerary_found = conn.execute(
                        text("SELECT trip_id FROM itineraries WHERE trip_id = :trip_id LIMIT 1"),
                        {"trip_id": smoke_trip_id},
                    ).scalar_one_or_none()
                    if not itinerary_found:
                        raise RuntimeError("itineraries row not found")

                return "users/trips/itineraries rows verified"

            results.append(_run_step("db_verify", _db_verify))

    # Print compact report
    print("\n=== SafePassage Smoke Flow ===")
    for result in results:
        marker = "PASS" if result.ok else "FAIL"
        print(f"[{marker}] {result.name} ({result.duration_ms}ms) - {result.detail}")

    all_ok = all(result.ok for result in results)

    if args.cleanup and args.db_url:
        cleanup_errors: list[str] = []
        try:
            cleanup_engine = create_engine(args.db_url, pool_pre_ping=True)
            with cleanup_engine.begin() as conn:
                conn.execute(text("DELETE FROM itineraries WHERE trip_id = :trip_id"), {"trip_id": smoke_trip_id})
                conn.execute(text("DELETE FROM heartbeats WHERE trip_id = :trip_id"), {"trip_id": smoke_trip_id})
                conn.execute(text("DELETE FROM trips WHERE id = :trip_id"), {"trip_id": smoke_trip_id})
                conn.execute(text("DELETE FROM emergency_contacts WHERE user_id = :user_id"), {"user_id": smoke_user_id})
                conn.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": smoke_user_id})
            print("[PASS] cleanup - removed smoke rows")
        except Exception as exc:
            cleanup_errors.append(str(exc))
            print(f"[FAIL] cleanup - {exc}")
            all_ok = False

    if not all_ok:
        print("\nSmoke flow FAILED.")
        return 1

    print("\nSmoke flow PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
