"""Edit formats — the ablation dial (harness component #3).

Three formats supported:
  - str_replace  : exact-match search/replace with read-before-edit enforcement
  - whole_file   : full file rewrite (fallback when str_replace fails repeatedly)
  - patch        : unified diff (optional; not the default)

All edits are atomic: write to a tmp file then rename.
"""
from harness.edit_formats.base import EditError, EditResult
from harness.edit_formats.patch import apply_patch
from harness.edit_formats.str_replace import mark_read, str_replace_edit
from harness.edit_formats.whole_file import whole_file_write

__all__ = [
    "EditResult",
    "EditError",
    "str_replace_edit",
    "mark_read",
    "whole_file_write",
    "apply_patch",
]
