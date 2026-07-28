"""Title hierarchy tracker for silver stage processing."""

from __future__ import annotations


class TitleTracker:
    """Tracks title hierarchy across pages using a stack-based approach.

    When a new title at level N is encountered, all titles at level >= N
    are popped, then the new title is pushed. This maintains a clean
    hierarchy where each page can render its full title context.
    """

    def __init__(self) -> None:
        self.stack: list[tuple[int, str]] = []

    def update(self, level: int, content: str) -> None:
        """Update the title hierarchy with a new title.

        Pops all titles at the same or deeper level, then pushes the new one.
        """
        while self.stack and self.stack[-1][0] >= level:
            self.stack.pop()
        self.stack.append((level, content))

    def get_hierarchy_markdown(self) -> str:
        """Render the current title stack as markdown headers."""
        if not self.stack:
            return ""
        return "\n".join(f"{'#' * (lvl + 1)} {txt}" for lvl, txt in self.stack)

    def get_session_title(self) -> str:
        """Get a compact session title string from the current stack."""
        if not self.stack:
            return ""
        return self.get_hierarchy_markdown() + "\n"
