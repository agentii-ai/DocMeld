"""Progress indicator utility for pipeline operations."""

from __future__ import annotations

import sys
from typing import IO


class ProgressTracker:
    """Tracks and displays progress for pipeline operations."""

    def update(
        self,
        current: int,
        total: int,
        message: str,
        output: IO[str] | None = None,
    ) -> None:
        """Print a progress update.

        Args:
            current: Current item number.
            total: Total number of items.
            message: Description of current operation.
            output: Output stream (defaults to stderr).
        """
        stream = output if output is not None else sys.stderr
        pct = int(current / total * 100) if total > 0 else 0
        line = f"{message}: {current}/{total} ({pct}%)\n"
        stream.write(line)
        stream.flush()
