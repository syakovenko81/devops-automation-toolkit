from .checker import check_url
from .errors import ErrorDescription, ResourceCheckError


__version__ = "0.1.0"

__all__ = [
    "ErrorDescription",
    "ResourceCheckError",
    "check_url",
]
