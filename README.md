# CheckStack

CheckStack is an open source, Kubernetes native uptime monitoring and SLA tracking platform that helps teams detect outages, measure reliability, and generate incident insights with minimal setup.

## What ships today

- **API** (`services/api`): FastAPI service for monitors, check history, SLA windows (24h / 7d), and incidents.
- **Worker** (`services/api`): Async uptime poller with retries/timeouts that records each check in both `check_results` and `uptime_log`, probes **TLS certificate expiry** for `https://` monitors (leaf cert, no chain validation), opens incidents after consecutive failures, and resolves them after sustained recovery (with debounce protection).
- **Web** (`services/web`): Next.js dashboard with monitor management (including assigning existing tags and creating comma-separated new tags inline), SLA cards, latency charting, and incident actions.
- **Infra**: Docker Compose for local installs, a Helm chart under `infra/helm/checkstack`, and sample Postgres manifests in `infra/k8s/postgres.yaml`.

## Quick start (Docker Compose)

```bash
make up
```

Then open `http://localhost:3000` for the dashboard and `http://localhost:8000/healthz` for API health.

The UI calls the API through same-origin `/api/...`, proxied by the Next server using **runtime** `INTERNAL_API_URL` (for example `http://api:8000` in Compose). That value is read per request, so you do not need web image rebuilds when the internal API hostname changes.

## Kubernetes (Helm)

Point `database.url` at a reachable Postgres DSN, build/push the `checkstack/api` and `checkstack/web` images referenced in `infra/helm/checkstack/values.yaml`, then:

```bash
helm upgrade --install checkstack ./infra/helm/checkstack \
  --set database.url=postgresql+psycopg://user:pass@host:5432/checkstack
```

The chart sets `INTERNAL_API_URL` automatically so the web pod can proxy to the API service.

## Configuration

Environment variables are read by `services/api/app/config.py`. Common keys:

- `DATABASE_URL` (required outside the bundled Compose file defaults)
- `CHECK_INTERVAL_SECONDS` (worker loop cadence; monitors still respect per-monitor intervals)
- `CHECK_TIMEOUT_SECONDS` (default request timeout for checks, unless monitor timeout overrides it)
- `CHECK_RETRY_ATTEMPTS` (retry attempts per check before a monitor is marked down)
- `INCIDENT_OPEN_AFTER_FAILURES` (global consecutive failure threshold to open incidents; default `3`)
- `INCIDENT_CLOSE_AFTER_SUCCESSES` (consecutive success threshold to close incidents; default `2`)
- `INCIDENT_DEBOUNCE_SECONDS` (minimum seconds between incident state transitions to reduce flapping)

## Development

```bash
cd services/api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite+pysqlite:///:memory: pytest -q

cd services/web && npm install && npm run dev
```

## License

MIT — see `LICENSE`.
