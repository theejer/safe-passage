"""Service for extracting itinerary data from uploaded documents using AI.

Handles:
1. Text extraction from PDF/DOCX/TXT inputs
2. LLM parsing to structured itinerary JSON
3. Fallback to manual parsing if LLM unavailable
"""

import json
import os
from typing import Any

import pdfplumber
from openai import OpenAI, APIError

try:
    from docx import Document
except Exception:
    Document = None

from app.utils.logging import get_logger

logger = get_logger(__name__)


def extract_itinerary_from_document(file_path: str) -> dict[str, Any]:
    """Extract itinerary from a supported document file using AI parsing.
    
    Args:
        file_path: Absolute path to source document (.pdf/.docx/.txt)
        
    Returns:
        Structured itinerary dict with 'days' and 'meta' keys
    """
    itinerary_text = _extract_document_text(file_path)
    if not itinerary_text.strip():
        logger.warning(f"No text extracted from itinerary document: {file_path}")
        return {"days": [], "meta": {}}

    logger.info(
        "[ItineraryParser] Extracted text length=%s preview=%s",
        len(itinerary_text),
        itinerary_text[:800],
    )

    return extract_itinerary_from_text(itinerary_text)


def extract_itinerary_from_pdf(file_path: str) -> dict[str, Any]:
    """Backwards-compatible wrapper for older callers expecting PDF-only API."""
    return extract_itinerary_from_document(file_path)


def extract_itinerary_from_text(itinerary_text: str) -> dict[str, Any]:
    """Extract itinerary JSON from raw itinerary text."""
    if not itinerary_text.strip():
        return {"days": [], "meta": {}}

    # Step 2: Use LLM to structure text
    try:
        itinerary = _parse_with_llm(itinerary_text)
        logger.info(f"Successfully parsed itinerary text with {len(itinerary.get('days', []))} days")
        return itinerary
    except (APIError, ValueError) as e:
        logger.warning(f"LLM parsing failed: {e}, attempting fallback parsing")
        # Fallback: basic text parsing if LLM unavailable
        return _parse_with_fallback(itinerary_text)


def _extract_document_text(file_path: str) -> str:
    """Extract text from supported itinerary document formats."""
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".pdf":
        return _extract_pdf_text(file_path)
    if extension == ".docx":
        return _extract_docx_text(file_path)
    if extension in {".txt", ".md", ".csv", ".doc"}:
        return _extract_plain_text(file_path)

    logger.warning("Unsupported itinerary document extension: %s", extension)
    return ""


def _extract_pdf_text(file_path: str) -> str:
    """Extract all text from PDF file."""
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(text)
                
                # Also try table extraction if available
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            text_parts.append(" | ".join(str(cell or "") for cell in row))

        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def _extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX files when python-docx is available."""
    if Document is None:
        logger.error("DOCX parsing requires python-docx; install dependency first")
        return ""

    try:
        document = Document(file_path)
        lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text and paragraph.text.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"DOCX text extraction failed: {e}")
        return ""


def _extract_plain_text(file_path: str) -> str:
    """Extract text from plain text-like files using best-effort decoding."""
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding, errors="ignore") as handle:
                return handle.read()
        except Exception:
            continue

    logger.error("Plain text extraction failed for file: %s", file_path)
    return ""


def _parse_with_llm(pdf_text: str) -> dict[str, Any]:
    """Use OpenAI GPT to structure itinerary text into JSON format.
    
    Expected output format:
    {
        "days": [
            {
                "date": "YYYY-MM-DD",
                "locations": [
                    {"name": "City", "district": "District", "block": "Block"}
                ],
                "accommodation": "Hotel name"
            }
        ],
        "meta": {}
    }
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)

    prompt = f"""Extract trip itinerary details from the following text and return a JSON object.

Only return valid JSON with this structure:
{{
    "days": [
        {{
            "date": "YYYY-MM-DD",
            "locations": [
                {{"name": "place name", "district": "district if available", "block": "block if available"}}
            ],
            "accommodation": "accommodation name if mentioned"
        }}
    ],
    "meta": {{}}
}}

Rules:
- If dates are not explicitly given, infer from day numbers (Day 1, Day 2, etc.)
- Locations must include at least the place name
- Extract all locations mentioned in the itinerary
- For Bihar locations: prioritize known districts like Patna, Nalanda, Gaya, Bhojpur, etc.
- If no accommodation info, leave that field empty or null
- Return ONLY valid JSON, no markdown code blocks

Text to parse:
{pdf_text[:3000]}  # Limit to first 3000 chars to avoid token overflow
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a travel itinerary parser. Extract trip details and return valid JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
        max_tokens=1000,
    )

    try:
        content = response.choices[0].message.content or ""
        # Clean up response (remove markdown code blocks if present)
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.split("```")[0]

        parsed = json.loads(content)
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError("LLM response was not valid JSON")


def _parse_with_fallback(pdf_text: str) -> dict[str, Any]:
    """Basic fallback parsing when LLM is unavailable.
    
    Looks for common patterns like "Day 1:", "Location:", etc.
    """
    days = []
    lines = pdf_text.split("\n")
    
    current_day = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for day indicators
        if "day" in line.lower() and any(c.isdigit() for c in line):
            if current_day:
                days.append(current_day)
            
            # Extract day number if possible
            date_str = line.split(":")[-1].strip() if ":" in line else ""
            current_day = {
                "date": date_str or "TBD",
                "locations": [],
                "accommodation": None,
            }
        
        # Look for location indicators
        elif current_day and any(marker in line.lower() for marker in ["location:", "visit:", "place:", "•", "-"]):
            location_name = line.lstrip("•-").strip().split(":")[1] if ":" in line else line.lstrip("•-").strip()
            if location_name:
                current_day["locations"].append({"name": location_name})
        
        # Look for accommodation
        elif current_day and any(marker in line.lower() for marker in ["stay:", "accommodation:", "hotel:", "lodge:"]):
            accommodation = line.split(":")[-1].strip()
            if accommodation:
                current_day["accommodation"] = accommodation

    if current_day:
        days.append(current_day)

    return {"days": days, "meta": {}}
