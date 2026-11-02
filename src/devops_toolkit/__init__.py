__version__ = "0.1.0"

__all__ = [
    "ErrorDescription",
    "ResourceCheckError",
    "check_url",
]


def __getattr__(name):
    """Load public objects only when they are imported by a consumer."""
    if name == "check_url":
        from .checker import check_url

        return check_url
    if name in {"ErrorDescription", "ResourceCheckError"}:
        from .errors import ErrorDescription, ResourceCheckError

        return {
            "ErrorDescription": ErrorDescription,
            "ResourceCheckError": ResourceCheckError,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
