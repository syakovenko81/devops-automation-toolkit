# DevOps Resource Checker

A small Python module and direct script for checking HTTP and HTTPS resources.
The checker reports the HTTP status, response time, and a useful error
category when the request cannot be completed.

## Setup

The project uses `requests` for HTTP checks and pytest for tests.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the checker

Run the Python module directly:

```bash
PYTHONPATH=src python -m devops_toolkit.checker https://example.com
PYTHONPATH=src python -m devops_toolkit.checker https://example.com --timeout 3
```

## Exit codes

When run as a script:

- `0` — successful HTTP response;
- `1` — HTTP error status;
- `2` — invalid input or request failure.

## Reuse the module

The HTTP logic can be imported without starting the checker script. A working
example is available in [`check_resource.py`](check_resource.py) in the project
root:

```python
from devops_toolkit.checker import check_url

result = check_url("https://example.com", timeout=3)
if result["result"]:
    print(result["status_code"], result["response_time"])
else:
    print(result["error_type"], result["message"])
```

Run the example from the project root:

```bash
PYTHONPATH=src python check_resource.py
```

This interface is intentionally small. It demonstrates reusable module
boundaries and direct unit testing, but it is not a complete organization-wide
library with packaging, versioning, ownership, or service governance.

## Tests and coverage

The tests mock the HTTP client and do not require public internet access.

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m pytest --cov=src/devops_toolkit --cov-report=term-missing
```

## Diagnostics

The checker logs the URL, HTTP status, response time, and error category.

To reproduce an HTTP error locally:

```bash
python3 -m http.server 8765
PYTHONPATH=src python -m devops_toolkit.checker http://127.0.0.1:8765/missing
```

The simulated incident and its investigation are documented in
[`docs/post-mortem.md`](docs/post-mortem.md).
