import argparse
import logging
import time
from urllib.parse import urlparse

import requests


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class ErrorDescription:
    """Error types and user-facing descriptions used by the checker."""

    INVALID_INPUT = "invalid_input"
    HTTP = "http_error"
    SSL = "ssl_error"
    TIMEOUT = "timeout"
    CONNECTION = "connection_error"
    REQUEST = "request_error"

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


def check_url(url: str, timeout: float = 10) -> dict:
    """
    Check an HTTP or HTTPS resource.

    Returns a dictionary with the result, HTTP status, response time, and
    message. HTTP responses and request failures are kept distinct.
    """
    started_at = time.perf_counter()
    response = None

    try:
        if not isinstance(url, str):
            raise ValueError("URL must be a valid HTTP or HTTPS URL")
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            raise ValueError("URL must be a valid HTTP or HTTPS URL")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("Timeout must be a positive number")

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        response_time = round(time.perf_counter() - started_at, 4)
        message = f"HTTP {response.status_code} returned in {response_time:.4f}s"
        logger.info("URL: %s; %s", url, message)
        return {
            "result": True,
            "status_code": response.status_code,
            "response_time": response_time,
            "message": message,
        }
    except ValueError as error:
        response_time = round(time.perf_counter() - started_at, 4)
        error_type = ErrorDescription.INVALID_INPUT
        message = ErrorDescription.get_message(error_type, error)
        logger.error("%s", message)
        return {
            "result": False,
            "status_code": None,
            "response_time": response_time,
            "error_type": error_type,
            "message": message,
        }
    except requests.exceptions.HTTPError as error:
        response_time = round(time.perf_counter() - started_at, 4)
        status_code = response.status_code if response is not None else None
        error_type = ErrorDescription.HTTP
        reason = response.reason if response is not None else None
        message = ErrorDescription.get_message(error_type, error, status_code, reason)
        logger.warning("URL: %s; %s", url, message)
        logger.debug("URL: %s; Details: %s", url, error)
        return {
            "result": False,
            "status_code": status_code,
            "response_time": response_time,
            "error_type": error_type,
            "message": message,
        }
    except requests.exceptions.SSLError as error:
        response_time = round(time.perf_counter() - started_at, 4)
        error_type = ErrorDescription.SSL
        message = ErrorDescription.get_message(error_type, error)
        logger.warning("URL: %s; %s", url, message)
        logger.debug("URL: %s; Details: %s", url, error)
        return {
            "result": False,
            "status_code": None,
            "response_time": response_time,
            "error_type": error_type,
            "message": message,
        }
    except requests.exceptions.Timeout as error:
        response_time = round(time.perf_counter() - started_at, 4)
        error_type = ErrorDescription.TIMEOUT
        message = ErrorDescription.get_message(error_type, error)
        logger.warning("URL: %s; %s", url, message)
        logger.debug("URL: %s; Details: %s", url, error)
        return {
            "result": False,
            "status_code": None,
            "response_time": response_time,
            "error_type": error_type,
            "message": message,
        }
    except requests.exceptions.ConnectionError as error:
        response_time = round(time.perf_counter() - started_at, 4)
        error_type = ErrorDescription.CONNECTION
        message = ErrorDescription.get_message(error_type, error)
        logger.warning("URL: %s; %s", url, message)
        logger.debug("URL: %s; Details: %s", url, error)
        return {
            "result": False,
            "status_code": None,
            "response_time": response_time,
            "error_type": error_type,
            "message": message,
        }
    except requests.exceptions.RequestException as error:
        response_time = round(time.perf_counter() - started_at, 4)
        error_type = ErrorDescription.REQUEST
        message = ErrorDescription.get_message(error_type, error)
        logger.warning("URL: %s; %s", url, message)
        logger.debug("URL: %s; Details: %s", url, error)
        return {
            "result": False,
            "status_code": None,
            "response_time": response_time,
            "error_type": error_type,
            "message": message,
        }


def main(arguments=None) -> int:
    parser = argparse.ArgumentParser(description="Check an HTTP or HTTPS resource")
    parser.add_argument("url", help="HTTP or HTTPS resource URL")
    parser.add_argument("--timeout", type=float, default=10, help="Request timeout in seconds")
    args = parser.parse_args(arguments)

    result = check_url(args.url, timeout=args.timeout)
    print(f"{args.url}: {result['message']}")

    if result["result"]:
        return 0
    if result.get("error_type") == ErrorDescription.HTTP:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
