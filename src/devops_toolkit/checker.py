import argparse
import logging
import time
import uuid
from urllib.parse import urlparse

import requests

from .errors import ErrorDescription, ResourceCheckError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _build_error_result(error: ResourceCheckError, started_at: float) -> dict:
    response_time = round(time.perf_counter() - started_at, 4)
    if error.error_type == ErrorDescription.INVALID_INPUT:
        logger.error("trace_id=%s %s", error.trace_id, error.message)
    else:
        logger.warning("trace_id=%s URL: %s; %s", error.trace_id, error.url, error.message)
        logger.debug(
            "trace_id=%s URL: %s; Details: %s",
            error.trace_id,
            error.url,
            error.__cause__ or error,
        )

    return {
        "result": False,
        "status_code": error.status_code,
        "response_time": response_time,
        "error_type": error.error_type,
        "message": error.message,
        "trace_id": error.trace_id,
    }


def check_url(url: str, timeout: float = 10) -> dict:
    """
    Check an HTTP or HTTPS resource.

    Returns a dictionary with the result, HTTP status, response time, and
    message. HTTP responses and request failures are kept distinct.
    """
    started_at = time.perf_counter()
    trace_id = uuid.uuid4().hex
    response = None

    try:
        try:
            logger.debug("trace_id=%s stage=validation URL: %s", trace_id, url)
            if not isinstance(url, str):
                raise ValueError("URL must be a valid HTTP or HTTPS URL")
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
                raise ValueError("URL must be a valid HTTP or HTTPS URL")
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError("Timeout must be a positive number")

            logger.debug("trace_id=%s stage=request URL: %s", trace_id, url)
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            response_time = round(time.perf_counter() - started_at, 4)
            message = f"HTTP {response.status_code} returned in {response_time:.4f}s"
            logger.info("trace_id=%s URL: %s; %s", trace_id, url, message)
            return {
                "result": True,
                "status_code": response.status_code,
                "response_time": response_time,
                "message": message,
                "trace_id": trace_id,
            }
        except ValueError as error:
            ErrorDescription.raise_from(
                ErrorDescription.INVALID_INPUT,
                error,
                url=url,
                trace_id=trace_id,
            )
        except requests.exceptions.HTTPError as error:
            status_code = response.status_code if response is not None else None
            reason = response.reason if response is not None else None
            ErrorDescription.raise_from(
                ErrorDescription.HTTP,
                error,
                url=url,
                status_code=status_code,
                reason=reason,
                trace_id=trace_id,
            )
        except requests.exceptions.SSLError as error:
            ErrorDescription.raise_from(
                ErrorDescription.SSL,
                error,
                url=url,
                trace_id=trace_id,
            )
        except requests.exceptions.Timeout as error:
            ErrorDescription.raise_from(
                ErrorDescription.TIMEOUT,
                error,
                url=url,
                trace_id=trace_id,
            )
        except requests.exceptions.ConnectionError as error:
            ErrorDescription.raise_from(
                ErrorDescription.CONNECTION,
                error,
                url=url,
                trace_id=trace_id,
            )
        except requests.exceptions.RequestException as error:
            ErrorDescription.raise_from(
                ErrorDescription.REQUEST,
                error,
                url=url,
                trace_id=trace_id,
            )
    except ResourceCheckError as error:
        return _build_error_result(error, started_at)


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
