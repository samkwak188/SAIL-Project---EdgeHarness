"""Edit-format base types."""
from dataclasses import dataclass


@dataclass
class EditResult:
    path: str
    bytes_written: int
    success: bool
    note: str = ""


class EditError(Exception):
    """Raised when an edit cannot be applied (stale file, no match, malformed patch)."""
