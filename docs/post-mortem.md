# Post-mortem: Resource Check Reported an Unavailable Endpoint

## Summary

The checker was run against a local HTTP server with a path that did not
exist. The command returned a non-zero status and reported the HTTP response
and elapsed time.

## Symptom

The automation step reported an error similar to:

```text
http://127.0.0.1:8765/missing: HTTP error 404: Test error
```

The process returned exit code `1`, so a CI or shell caller could stop the
automation step.

## Investigation

1. A local server was started with `python3 -m http.server 8765`.
2. The checker was run against `/missing`.
3. The URL, response status, and response time were compared between the log
   message and the command output.
4. The response status and response time showed that a server answered; this
   was not a DNS, connection, timeout, or SSL failure.

## Root cause

The requested path was absent from the local server directory. The endpoint
was reachable, but the application returned HTTP 404.

## Fix

The caller corrected the resource path and reran the check. The checker itself
did not retry the request because a 404 is an HTTP response and is normally a
permanent input or resource problem, not a transient connection failure.

## Prevention

- Keep the resource URL in configuration or review it before deployment.
- Use the checker exit code in automation and retain its log output.
- Add a mocked test for each important error category so changes do not merge
  without preserving the distinction between an HTTP response and a transport
  failure.

## Scope and limitations

The project does not implement distributed tracing, OpenTelemetry, or a remote
incident system. The `cProfile` command is an on-demand diagnostic example,
not continuous production profiling.
