"""Whole-file write — fallback edit format (error-recovery ladder rung 2)."""
from __future__ import annotations

from pathlib import Path

from harness.edit_formats.base import EditResult


def whole_file_write(path: str, content: str) -> EditResult:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".sail-tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)
    return EditResult(path=str(p), bytes_written=len(content), success=True, note="whole_file")
