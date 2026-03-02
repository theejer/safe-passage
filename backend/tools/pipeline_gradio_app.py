import json
from html import escape
from typing import Any
import sys
from pathlib import Path

import gradio as gr

REPO_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_BACKEND_ROOT))

from app.services.pipeline_backend import ANALYZER_MODEL, DEFAULT_MODEL, SOLO_TRAVELER_PROFILE, has_openai_config, run_itinerary_pipeline


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def render_score_html(final_report: dict[str, Any]) -> str:
    score = final_report.get("SCORE") if isinstance(final_report, dict) and isinstance(final_report.get("SCORE"), dict) else {}
    score_value = _as_int(score.get("value"), 0)
    score_justification = escape(str(score.get("justification", "")))

    score_class = "score-high"
    if score_value < 50:
        score_class = "score-low"
    elif score_value < 75:
        score_class = "score-medium"

    return f"""
    <div class='score-wrap'>
        <div class='score-label'>SCORE</div>
        <div class='score-value {score_class}'>{score_value}</div>
        <div class='score-why'>{score_justification}</div>
    </div>
    """


def build_day_payload(final_report: dict[str, Any]) -> tuple[list[str], dict[str, Any], str]:
    days = final_report.get("DAY") if isinstance(final_report, dict) and isinstance(final_report.get("DAY"), list) else []
    day_map: dict[str, Any] = {}
    labels: list[str] = []

    for day in days:
        if not isinstance(day, dict):
            continue
        day_id = str(day.get("day_id") or "")
        day_label = str(day.get("day_label") or day_id or "Unspecified")
        key = f"{day_label} [{day_id}]" if day_id else day_label
        day_map[key] = day
        labels.append(key)

    default_choice = labels[0] if labels else ""
    return labels, day_map, default_choice


def render_day_cards(day_entry: dict[str, Any] | None) -> str:
    if not isinstance(day_entry, dict):
        return "<div class='empty-box'>No day selected.</div>"

    activities = day_entry.get("ACTIVITY") if isinstance(day_entry.get("ACTIVITY"), list) else []
    if not activities:
        return "<div class='empty-box'>No activities available for this day.</div>"

    cards: list[str] = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue

        activity_name = escape(str(activity.get("activity", "Unnamed Activity")))
        location = activity.get("location")
        location_html = f"<div class='activity-location'>{escape(str(location))}</div>" if location else ""

        risks = activity.get("RISK") if isinstance(activity.get("RISK"), list) else []
        risk_blocks: list[str] = []

        if not risks:
            risk_blocks.append("<div class='risk-item'>No reportable risks for this activity.</div>")

        for risk in risks:
            if not isinstance(risk, dict):
                continue
            severity = escape(str(risk.get("severity", "Low")))
            domain = escape(str(risk.get("domain", "domain")))
            risk_title = escape(str(risk.get("risk", "Unspecified risk")))
            mitigation = escape(str(risk.get("mitigation", "")))
            details = escape(str(risk.get("details", "")))

            severity_class = "sev-low"
            if severity.lower() == "no":
                severity_class = "sev-none"
            if severity.lower() == "medium":
                severity_class = "sev-medium"
            elif severity.lower() == "high":
                severity_class = "sev-high"

            risk_blocks.append(
                f"""
                <div class='risk-item'>
                    <div class='risk-top'>
                        <span class='risk-domain'>{domain}</span>
                        <span class='risk-sev {severity_class}'>{severity}</span>
                    </div>
                    <div class='risk-title'>{risk_title}</div>
                    <div class='risk-details'>{details}</div>
                    <div class='risk-mitigation'><b>Mitigation:</b> {mitigation}</div>
                </div>
                """
            )

        cards.append(
            f"""
            <div class='activity-card'>
                <div class='activity-title'>{activity_name}</div>
                {location_html}
                <div class='risk-list'>{''.join(risk_blocks)}</div>
            </div>
            """
        )

    return f"<div class='activity-grid'>{''.join(cards)}</div>"


def on_day_change(selected_day: str, day_state: dict[str, Any]) -> str:
    if not isinstance(day_state, dict):
        return "<div class='empty-box'>No data loaded yet.</div>"
    return render_day_cards(day_state.get(selected_day))


def analyze_itinerary(user_itinerary: str, parser_model: str, analyzer_model: str) -> tuple[str, gr.update, str, str, str, str, dict[str, Any]]:
    itinerary_text = (user_itinerary or "").strip()
    if not itinerary_text:
        message = {"error": "Please paste an itinerary first."}
        return (
            "<div class='empty-box'>Please paste an itinerary first.</div>",
            gr.update(choices=[], value=None),
            "<div class='empty-box'>No day data yet.</div>",
            json.dumps(message, indent=2),
            "{}",
            "{}",
            {},
        )

    ok, error = has_openai_config()
    if not ok:
        payload = {"error": f"Configuration error: {error}"}
        return (
            f"<div class='empty-box'>{escape(payload['error'])}</div>",
            gr.update(choices=[], value=None),
            "<div class='empty-box'>No day data yet.</div>",
            json.dumps(payload, indent=2),
            "{}",
            "{}",
            {},
        )

    result = run_itinerary_pipeline(
        itinerary_text,
        model=(parser_model or DEFAULT_MODEL),
        analyzer_model=(analyzer_model or ANALYZER_MODEL),
    )

    if result.get("status") != "ok":
        payload = {"error": "Pipeline failed. See details.", "details": result}
        return (
            "<div class='empty-box'>Pipeline failed. Check JSON output.</div>",
            gr.update(choices=[], value=None),
            "<div class='empty-box'>No day data yet.</div>",
            json.dumps(payload, indent=2),
            json.dumps(result, indent=2),
            "{}",
            {},
        )

    final_report = result.get("final_report", {})
    parsed_json = json.dumps(result.get("parsed_itinerary", {}), indent=2)
    analyst_json = json.dumps(result.get("analyst_reports", {}), indent=2)
    final_json = json.dumps(final_report, indent=2)

    day_choices, day_map, selected = build_day_payload(final_report)
    day_cards_html = render_day_cards(day_map.get(selected)) if selected else "<div class='empty-box'>No day data returned.</div>"

    return (
        render_score_html(final_report),
        gr.update(choices=day_choices, value=selected),
        day_cards_html,
        final_json,
        parsed_json,
        analyst_json,
        day_map,
    )


with gr.Blocks(
    title="Travel Risk Pipeline",
    css="""
    .score-wrap { border: 1px solid #ddd; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 12px; }
    .score-label { font-size: 12px; font-weight: 700; letter-spacing: 1.4px; }
    .score-value { font-size: 56px; font-weight: 800; line-height: 1.1; margin-top: 4px; }
    .score-why { margin-top: 8px; font-size: 14px; }
    .score-high { color: #15803d; }
    .score-medium { color: #a16207; }
    .score-low { color: #b91c1c; }

    .activity-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .activity-card { border: 1px solid #ddd; border-radius: 10px; padding: 12px; }
    .activity-title { font-size: 15px; font-weight: 700; }
    .activity-location { font-size: 13px; opacity: 0.85; margin-top: 4px; margin-bottom: 8px; }

    .risk-list { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
    .risk-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; }
    .risk-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .risk-domain { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .risk-sev { font-size: 12px; font-weight: 700; border-radius: 999px; padding: 2px 8px; }
    .sev-none { background: #e5e7eb; color: #374151; }
    .sev-low { background: #dcfce7; color: #166534; }
    .sev-medium { background: #fef9c3; color: #854d0e; }
    .sev-high { background: #fee2e2; color: #991b1b; }
    .risk-title { font-size: 14px; font-weight: 700; margin-bottom: 3px; }
    .risk-details, .risk-mitigation { font-size: 13px; line-height: 1.4; }

    .empty-box { border: 1px dashed #bbb; border-radius: 10px; padding: 12px; font-size: 14px; }

    @media (max-width: 900px) {
      .activity-grid { grid-template-columns: 1fr; }
    }
    """,
) as demo:
    gr.Markdown("# Travel Risk Pipeline")
    gr.Markdown("Paste itinerary text, then run parser + 5 analyzers. Final output is DAY -> ACTIVITY -> RISK.")
    gr.Markdown(
        f"**Traveler Mode:** Solo traveler (group size {int(SOLO_TRAVELER_PROFILE.get('group_size', 1))})"
    )

    itinerary_input = gr.Textbox(
        label="User Itinerary",
        placeholder="Paste full itinerary text here...",
        lines=12,
    )

    with gr.Row():
        parser_model_input = gr.Textbox(label="Parser Model", value=DEFAULT_MODEL)
        analyzer_model_input = gr.Textbox(label="Analyzer Model", value=ANALYZER_MODEL)

    run_button = gr.Button("Analyze Trip")

    day_state = gr.State({})

    score_output = gr.HTML(label="Score")
    day_dropdown = gr.Dropdown(label="Day", choices=[], value=None)
    day_cards_output = gr.HTML(label="Day Activities & Risks")

    final_report_output = gr.Code(label="Final Report JSON", language="json")
    parsed_output = gr.Code(label="Parsed Itinerary JSON", language="json")
    analysts_output = gr.Code(label="Analyst Reports JSON", language="json")

    run_button.click(
        fn=analyze_itinerary,
        inputs=[itinerary_input, parser_model_input, analyzer_model_input],
        outputs=[
            score_output,
            day_dropdown,
            day_cards_output,
            final_report_output,
            parsed_output,
            analysts_output,
            day_state,
        ],
        concurrency_limit=1,
    )

    day_dropdown.change(
        fn=on_day_change,
        inputs=[day_dropdown, day_state],
        outputs=[day_cards_output],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    demo.launch(share=True)
