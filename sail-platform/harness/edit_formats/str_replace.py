"""str_replace edit format with read-before-edit enforcement."""
from __future__ import annotations

from pathlib import Path

from harness.edit_formats.base import EditError, EditResult

# Tracks files read in the current session — read_before_edit enforcement.
_read_tracker: set[str] = set()


def mark_read(path: str) -> None:
    _read_tracker.add(str(Path(path).resolve()))


def str_replace_edit(path: str, old_string: str, new_string: str, *, enforce_read: bool = True) -> EditResult:
    p = Path(path)
    if not p.exists():
        raise EditError(f"file not found: {path}")
    if enforce_read and str(p.resolve()) not in _read_tracker:
        raise EditError(f"read-before-edit violated: {path} was not read in this session")
    content = p.read_text(encoding="utf-8")
    if old_string not in content:
        raise EditError(f"old_string not found in {path}")
    occurrences = content.count(old_string)
    if occurrences > 1:
        raise EditError(f"old_string not unique in {path}: {occurrences} matches")
    new_content = content.replace(old_string, new_string, 1)
    _atomic_write(p, new_content)
    return EditResult(path=str(p), bytes_written=len(new_content), success=True, note="str_replace")


def _atomic_write(p: Path, content: str) -> None:
    tmp = p.with_suffix(p.suffix + ".sail-tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)
