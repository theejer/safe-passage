"""Tests for pipeline adapter request-to-service mapping."""

from app.services import pipeline_adapter


def test_analyze_trip_passes_form_fields_as_parser_context(monkeypatch):
    captured: dict = {}

    def _fake_run_itinerary_pipeline(itinerary, *, model, analyzer_model, parser_context=None):
        captured["itinerary"] = itinerary
        captured["model"] = model
        captured["analyzer_model"] = analyzer_model
        captured["parser_context"] = parser_context
        return {"status": "ok"}

    monkeypatch.setattr(pipeline_adapter, "run_itinerary_pipeline", _fake_run_itinerary_pipeline)

    payload = {
        "itinerary": "Day 1: Fly to Tokyo",
        "trip_name": "Japan Sprint",
        "start_date": "2026-04-01",
        "end_date": "2026-04-05",
        "destination_country": "jp",
    }

    result = pipeline_adapter.analyze_trip(payload)

    assert result == {"status": "ok"}
    assert captured["itinerary"] == "Day 1: Fly to Tokyo"
    assert captured["parser_context"]["trip_name"] == "Japan Sprint"
    assert captured["parser_context"]["start_date"] == "2026-04-01"
    assert captured["parser_context"]["end_date"] == "2026-04-05"
    assert captured["parser_context"]["destination_country"] == "JP"


def test_analyze_trip_parser_context_falls_back_to_metadata(monkeypatch):
    captured: dict = {}

    def _fake_run_itinerary_pipeline(itinerary, *, model, analyzer_model, parser_context=None):
        captured["parser_context"] = parser_context
        return {"status": "ok"}

    monkeypatch.setattr(pipeline_adapter, "run_itinerary_pipeline", _fake_run_itinerary_pipeline)

    payload = {
        "itinerary": "Day 1: Johor Bahru transfer",
        "metadata": {
            "trip_name": "Malaysia Quick Trip",
            "start_date": "2026-07-10",
            "end_date": "2026-07-12",
            "destination_country": "my",
        },
    }

    result = pipeline_adapter.analyze_trip(payload)

    assert result == {"status": "ok"}
    assert captured["parser_context"]["trip_name"] == "Malaysia Quick Trip"
    assert captured["parser_context"]["start_date"] == "2026-07-10"
    assert captured["parser_context"]["end_date"] == "2026-07-12"
    assert captured["parser_context"]["destination_country"] == "MY"
