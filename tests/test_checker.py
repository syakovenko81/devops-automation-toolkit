import os
import sys
import logging
from unittest.mock import MagicMock, patch

import pytest
import requests


SOURCE_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from devops_toolkit import (  # noqa: E402
    ErrorDescription as PublicErrorDescription,
    ResourceCheckError as PublicResourceCheckError,
    __version__,
    check_url as public_check_url,
)
from devops_toolkit.checker import ErrorDescription, check_url, main  # noqa: E402
from devops_toolkit.errors import ResourceCheckError, ResourceTimeoutError  # noqa: E402


def _response(status_code, reason="OK"):
    response = MagicMock()
    response.status_code = status_code
    response.reason = reason
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(reason)
    return response


def test_error_description_contains_error_types_and_messages():
    assert ErrorDescription.HTTP == "http_error"
    assert ErrorDescription.TIMEOUT == "timeout"
    assert ErrorDescription.get_message(ErrorDescription.HTTP, "Not Found", 404, "Not Found") == "HTTP error 404: Not Found"
    assert ErrorDescription.get_message(ErrorDescription.TIMEOUT, "request timed out") == "Request timeout: resource did not respond in time"
    assert ErrorDescription.get_message(ErrorDescription.CONNECTION, "Failed to resolve host") == "DNS error: unable to resolve host"


def test_package_exposes_stable_public_api():
    assert __version__ == "0.1.0"
    assert public_check_url is check_url
    assert PublicErrorDescription is ErrorDescription
    assert PublicResourceCheckError is ResourceCheckError


def test_error_description_creates_typed_error_with_context():
    error = ErrorDescription.create_error(
        ErrorDescription.TIMEOUT,
        "request timed out",
        url="https://example.com",
        trace_id="trace-123",
    )

    assert isinstance(error, ResourceTimeoutError)
    assert isinstance(error, ResourceCheckError)
    assert error.error_type == ErrorDescription.TIMEOUT
    assert error.url == "https://example.com"
    assert error.trace_id == "trace-123"
    assert error.message == "Request timeout: resource did not respond in time"


def test_error_description_preserves_original_cause():
    cause = requests.exceptions.Timeout("request timed out")

    with pytest.raises(ResourceTimeoutError) as caught:
        ErrorDescription.raise_from(
            ErrorDescription.TIMEOUT,
            cause,
            url="https://example.com",
            trace_id="trace-123",
        )

    assert caught.value.__cause__ is cause
    assert caught.value.trace_id == "trace-123"


def test_check_url_success_returns_status_and_response_time():
    with patch("devops_toolkit.checker.requests.get", return_value=_response(200)) as mock_get, \
         patch("devops_toolkit.checker.time.perf_counter", side_effect=[10.0, 10.125]):
        result = check_url("https://example.com", timeout=3)

    mock_get.assert_called_once_with("https://example.com", timeout=3)
    assert result["result"] is True
    assert result["status_code"] == 200
    assert result["response_time"] == 0.125
    assert len(result["trace_id"]) == 32


def test_check_url_uses_trace_id_for_debug_stages(caplog):
    caplog.set_level(logging.DEBUG)

    with patch("devops_toolkit.checker.requests.get", return_value=_response(200)):
        result = check_url("https://example.com")

    assert f"trace_id={result['trace_id']}" in caplog.text
    assert "stage=validation" in caplog.text
    assert "stage=request" in caplog.text


@pytest.mark.parametrize("status_code", [201, 204, 301])
def test_check_url_handles_success_http_statuses(status_code):
    with patch("devops_toolkit.checker.requests.get", return_value=_response(status_code)):
        result = check_url("https://example.com")

    assert result["result"] is True
    assert result["status_code"] == status_code


@pytest.mark.parametrize("status_code", [400, 404, 500])
def test_check_url_handles_http_errors(status_code):
    with patch("devops_toolkit.checker.requests.get", return_value=_response(status_code, "Test error")):
        result = check_url("https://example.com")

    assert result["result"] is False
    assert result["status_code"] == status_code
    assert result["error_type"] == "http_error"
    assert f"HTTP error {status_code}" in result["message"]


@pytest.mark.parametrize("url", [None, "", "example.com", "ftp://example.com", "http://"])
def test_check_url_rejects_invalid_urls(url):
    with patch("devops_toolkit.checker.requests.get") as mock_get:
        result = check_url(url)

    assert result["result"] is False
    assert result["error_type"] == "invalid_input"
    mock_get.assert_not_called()


def test_check_url_rejects_invalid_timeout():
    with patch("devops_toolkit.checker.requests.get") as mock_get:
        result = check_url("https://example.com", timeout=0)

    assert result["result"] is False
    assert result["error_type"] == "invalid_input"
    mock_get.assert_not_called()


def test_check_url_handles_timeout():
    with patch(
        "devops_toolkit.checker.requests.get",
        side_effect=requests.exceptions.Timeout("request timed out"),
    ):
        result = check_url("https://example.com", timeout=1)

    assert result["result"] is False
    assert result["error_type"] == "timeout"


def test_check_url_handles_dns_or_connection_error():
    with patch(
        "devops_toolkit.checker.requests.get",
        side_effect=requests.exceptions.ConnectionError("Name or service not known"),
    ):
        result = check_url("https://missing.example", timeout=1)

    assert result["result"] is False
    assert result["error_type"] == "connection_error"
    assert result["message"] == "DNS error: unable to resolve host"
    assert result["trace_id"]


def test_check_url_handles_connection_error():
    with patch(
        "devops_toolkit.checker.requests.get",
        side_effect=requests.exceptions.ConnectionError("connection refused"),
    ):
        result = check_url("http://127.0.0.1:1", timeout=1)

    assert result["result"] is False
    assert result["error_type"] == "connection_error"
    assert result["message"] == "Connection error: unable to connect to resource"


def test_check_url_handles_ssl_error():
    with patch(
        "devops_toolkit.checker.requests.get",
        side_effect=requests.exceptions.SSLError("certificate verify failed"),
    ):
        result = check_url("https://example.com", timeout=1)

    assert result["result"] is False
    assert result["error_type"] == "ssl_error"
    assert result["message"] == "SSL error: unable to establish secure connection"


def test_check_url_handles_other_request_error():
    with patch(
        "devops_toolkit.checker.requests.get",
        side_effect=requests.exceptions.RequestException("request failed"),
    ):
        result = check_url("https://example.com")

    assert result["result"] is False
    assert result["error_type"] == "request_error"


def test_check_url_is_importable_without_cli_module():
    with patch("devops_toolkit.checker.requests.get", return_value=_response(200)):
        result = check_url("http://localhost:8765")

    assert result["status_code"] == 200


def test_main_returns_http_error_exit_code(capsys):
    result = {
        "result": False,
        "status_code": 404,
        "response_time": 0.01,
        "error_type": "http_error",
        "message": "HTTP error 404",
    }
    with patch("devops_toolkit.checker.check_url", return_value=result):
        exit_code = main(["https://example.com/missing"])

    assert exit_code == 1
    assert "HTTP error 404" in capsys.readouterr().out


def test_main_returns_request_error_exit_code():
    result = {
        "result": False,
        "status_code": None,
        "response_time": 0.01,
        "error_type": "timeout",
        "message": "Request timeout",
    }
    with patch("devops_toolkit.checker.check_url", return_value=result):
        assert main(["https://example.com"]) == 2


def test_main_returns_success_exit_code(capsys):
    result = {
        "result": True,
        "status_code": 200,
        "response_time": 0.01,
        "message": "HTTP 200 returned in 0.0100s",
    }
    with patch("devops_toolkit.checker.check_url", return_value=result):
        assert main(["https://example.com"]) == 0

    assert "HTTP 200" in capsys.readouterr().out
