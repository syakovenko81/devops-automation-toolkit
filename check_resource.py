from devops_toolkit.checker import check_url


CHECKS = [
    ("HTTP 200 example.com", "https://example.com", 10),
    ("HTTP 200", "https://httpbin.org/status/200", 10),
    ("HTTP 201", "https://httpbin.org/status/201", 10),
    ("HTTP 204", "https://httpbin.org/status/204", 10),
    ("HTTP 400", "https://httpbin.org/status/400", 10),
    ("HTTP 404", "https://httpbin.org/status/404", 10),
    ("HTTP 500", "https://httpbin.org/status/500", 10),
    ("Invalid URL without scheme", "example.com", 10),
    ("Invalid URL scheme", "ftp://example.com", 10),
    ("Invalid URL without host", "http://", 10),
    ("Invalid timeout", "https://example.com", 0),
    ("DNS error", "https://does-not-exist.invalid", 10),
    ("Connection error", "http://127.0.0.1:1", 10),
    ("SSL error", "https://expired.badssl.com", 10),
    ("Request timeout", "https://httpbin.org/delay/10", 0.1),
]


for name, url, timeout in CHECKS:
    result = check_url(url, timeout=timeout)
    print(f"--- {name} ---")
    print(f"URL: {url}")
    print(f"Result: {result['message']}")
    print(f"Error type: {result.get('error_type', 'none')}")
    print(f"Response time: {result['response_time']}s")
