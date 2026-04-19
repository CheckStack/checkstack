# Example API responses

All paths are under the CheckStack API base, for example `http://localhost:8000` (or proxied as `/api` in the Next app).

## `GET /monitors`

List monitors; optional `?tag_id=1` filters to monitors that have that tag.

```json
[
  {
    "id": 1,
    "name": "API",
    "url": "https://api.example.com/healthz",
    "interval_seconds": 60,
    "timeout_seconds": 10,
    "failure_threshold": 3,
    "consecutive_failures": 0,
    "alerts_enabled": true,
    "last_status": "up",
    "last_checked_at": "2026-04-18T10:00:00Z",
    "tags": [{ "id": 2, "name": "prod", "color": "#22c55e" }],
    "alerts_will_fire": true,
    "created_at": "2026-04-01T12:00:00Z"
  }
]
```

## `GET /public/status`

Public, no auth, for a status page.

```json
{
  "monitors": [
    {
      "id": 1,
      "name": "API",
      "url": "https://api.example.com/healthz",
      "status": "up",
      "sla_24h_percent": 99.95
    }
  ]
}
```

## `GET /uptime/1?range=24h`

Uptime and response time series from stored check results.

```json
{
  "monitor_id": 1,
  "range": "24h",
  "from": "2026-04-17T10:00:00Z",
  "to": "2026-04-18T10:00:00Z",
  "points": [
    {
      "t": "2026-04-18T09:55:00Z",
      "status": "success",
      "ok": true,
      "response_time_ms": 45.2,
      "status_code": 200
    }
  ]
}
```

## `GET /monitors/1/stats?window=24h`

```json
{
  "monitor_id": 1,
  "window": "24h",
  "avg_latency_ms": 52.1,
  "p95_latency_ms": 120.0,
  "min_latency_ms": 12.0,
  "max_latency_ms": 200.0,
  "total_checks": 1440,
  "with_latency": 1400,
  "sla": {
    "monitor_id": 1,
    "window": "24h",
    "uptime_percent": 99.93,
    "total_checks": 1440,
    "successful_checks": 1438
  }
}
```

## `GET /incidents/1`

```json
{
  "id": 1,
  "monitor_id": 1,
  "title": "API — down",
  "summary": "3 consecutive check failures (timeout).",
  "status": "resolved",
  "detected_by": "uptime_worker",
  "started_at": "2026-04-18T08:00:00Z",
  "resolved_at": "2026-04-18T08:05:00Z",
  "duration_seconds": 300,
  "start_time": "2026-04-18T08:00:00Z",
  "end_time": "2026-04-18T08:05:00Z",
  "monitor_name": "API",
  "monitor_url": "https://api.example.com/healthz"
}
```

## `POST /tags` — `POST /alerts`

Create a tag: `{"name": "prod", "color": "#22c55e"}`.

Create a Slack channel (global): `{"kind": "slack", "name": "on-call", "config": {"webhook_url": "https://hooks.slack.com/…"}, "enabled": true}`.

Create an email channel: `{"kind": "email", "name": "team", "config": {"to": "ops@example.com"}, "enabled": true}`.

`DELETE /alerts/{id}` returns **204 No Content** with an empty body.

## Environment

Copy `.env.example` in the repo root. Key variables for alert delivery and public links: `PUBLIC_BASE_URL`, `SMTP_*`, and optional `SLACK_DEFAULT_WEBHOOK_URL`.
