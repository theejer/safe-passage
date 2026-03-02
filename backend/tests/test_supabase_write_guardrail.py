"""Guardrail tests for Supabase table-write usage.

Any direct Supabase table writes must be paired with offline mirror handling.
Until that contract is explicitly introduced, backend persistence should remain
on SQLAlchemy engine write paths.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_no_direct_supabase_table_writes_in_backend_app():
    app_root = Path(__file__).resolve().parents[1] / "app"
    forbidden_write_patterns = [
        re.compile(r"get_supabase\(\)\s*\.\s*(?:table|from_)\s*\(", re.IGNORECASE),
        re.compile(r"create_client\([^)]*\)\s*\.\s*(?:table|from_)\s*\(", re.IGNORECASE),
    ]

    violating_files: list[str] = []

    for file_path in app_root.rglob("*.py"):
        content = file_path.read_text(encoding="utf-8")
        if any(pattern.search(content) for pattern in forbidden_write_patterns):
            violating_files.append(str(file_path.relative_to(app_root.parent)).replace("\\", "/"))

    assert not violating_files, (
        "Direct Supabase table write access detected. "
        "Use SQLAlchemy-backed model write paths and mirror strategy instead. "
        f"Violations: {violating_files}"
    )
