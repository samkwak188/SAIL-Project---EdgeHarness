"""Unified-diff patch applier — optional third edit format."""
from __future__ import annotations

import re
from pathlib import Path

from harness.edit_formats.base import EditError, EditResult

_HUNK_RE = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", re.MULTILINE)


def apply_patch(path: str, patch: str) -> EditResult:
    p = Path(path)
    if not p.exists():
        raise EditError(f"file not found: {path}")
    content = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    cursor = 0
    for m in _HUNK_RE.finditer(patch):
        old_start = int(m.group(1))
        # find hunk body
        body_start = m.end()
        next_hunk = _HUNK_RE.search(patch, body_start)
        body = patch[body_start : next_hunk.start() if next_hunk else len(patch)]
        # copy unchanged lines before this hunk
        out.extend(content[cursor : old_start - 1])
        for line in body.splitlines(keepends=True):
            if line.startswith(" "):
                out.append(line[1:])
            elif line.startswith("-"):
                continue
            elif line.startswith("+"):
                out.append(line[1:])
            elif line.startswith("@"):
                continue
        cursor = old_start - 1 + sum(1 for ln in body.splitlines() if ln.startswith((" ", "-")))
    out.extend(content[cursor:])
    new_content = "".join(out)
    tmp = p.with_suffix(p.suffix + ".sail-tmp")
    tmp.write_text(new_content, encoding="utf-8")
    tmp.replace(p)
    return EditResult(path=str(p), bytes_written=len(new_content), success=True, note="patch")
