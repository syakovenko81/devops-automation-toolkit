import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests


SOURCE_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from devops_toolkit.checker import ErrorDescription, check_url, main  # noqa: E402


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


def test_check_url_success_returns_status_and_response_time():
    with patch("devops_toolkit.checker.requests.get", return_value=_response(200)) as mock_get, \
         patch("devops_toolkit.checker.time.perf_counter", side_effect=[10.0, 10.125]):
        result = check_url("https://example.com", timeout=3)

    mock_get.assert_called_once_with("https://example.com", timeout=3)
    assert result["result"] is True
    assert result["status_code"] == 200
    assert result["response_time"] == 0.125


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
