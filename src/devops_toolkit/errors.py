class ResourceCheckError(Exception):
    """Base class for errors raised while checking a resource."""

    error_type = "request_error"

    def __init__(self, message, *, url=None, status_code=None):
        super().__init__(message)
        self.message = message
        self.url = url
        self.status_code = status_code


class InvalidInputError(ResourceCheckError):
    error_type = "invalid_input"


class HttpStatusError(ResourceCheckError):
    error_type = "http_error"


class ResourceSslError(ResourceCheckError):
    error_type = "ssl_error"


class ResourceTimeoutError(ResourceCheckError):
    error_type = "timeout"


class ResourceConnectionError(ResourceCheckError):
    error_type = "connection_error"


class ResourceRequestError(ResourceCheckError):
    error_type = "request_error"


class ErrorDescription:
    """Error types, messages, and domain error creation for the checker."""

    INVALID_INPUT = InvalidInputError.error_type
    HTTP = HttpStatusError.error_type
    SSL = ResourceSslError.error_type
    TIMEOUT = ResourceTimeoutError.error_type
    CONNECTION = ResourceConnectionError.error_type
    REQUEST = ResourceRequestError.error_type

    _ERROR_CLASSES = {
        INVALID_INPUT: InvalidInputError,
        HTTP: HttpStatusError,
        SSL: ResourceSslError,
        TIMEOUT: ResourceTimeoutError,
        CONNECTION: ResourceConnectionError,
        REQUEST: ResourceRequestError,
    }

    @classmethod
    def get_message(cls, error_type: str, error, status_code=None, reason=None) -> str:
        if error_type == cls.HTTP:
            return f"HTTP error {status_code}: {reason or 'server returned an error'}"

        if error_type == cls.CONNECTION:
            error_message = str(error).lower()
            if (
                "resolve" in error_message
                or "name resolution" in error_message
                or "name or service not known" in error_message
            ):
                return "DNS error: unable to resolve host"
            return "Connection error: unable to connect to resource"

        messages = {
            cls.INVALID_INPUT: "Invalid request data",
            cls.SSL: "SSL error: unable to establish secure connection",
            cls.TIMEOUT: "Request timeout: resource did not respond in time",
            cls.REQUEST: "Request error: unable to complete request",
        }
        if error_type == cls.INVALID_INPUT:
            return f"{messages[error_type]}: {error}"
        return messages[error_type]

    @classmethod
    def create_error(cls, error_type, error, url=None, status_code=None, reason=None):
        message = cls.get_message(error_type, error, status_code, reason)
        error_class = cls._ERROR_CLASSES[error_type]
        return error_class(message, url=url, status_code=status_code)

    @classmethod
    def raise_from(cls, error_type, cause, url=None, status_code=None, reason=None):
        """Raise a domain error while preserving the low-level cause."""
        raise cls.create_error(
            error_type,
            cause,
            url=url,
            status_code=status_code,
            reason=reason,
        ) from cause
