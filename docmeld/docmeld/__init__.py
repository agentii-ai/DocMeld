"""DocMeld - Lightweight PDF to agent-ready knowledge pipeline."""

__version__ = "0.2.0"

# Lazy import to avoid side effects on import
def __getattr__(name: str) -> object:
    if name == "DocMeldParser":
        from docmeld.parser import DocMeldParser
        return DocMeldParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["DocMeldParser", "__version__"]
