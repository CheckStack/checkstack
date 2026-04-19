# CheckStack

CheckStack is an open source, Kubernetes native uptime monitoring and SLA tracking platform that helps teams detect outages, measure reliability, and generate incident insights with minimal setup.

## What ships today

- **API** (`services/api`): FastAPI service for monitors, check history, SLA windows (24h / 7d), and incidents.
- **Worker** (`services/api`): Async uptime poller that records results, opens incidents after consecutive failures, and resolves them when checks recover.
- **Web** (`services/web`): Next.js dashboard with monitor management, SLA cards, latency charting, and incident actions.
- **Infra**: Docker Compose for local installs, a Helm chart under `infra/helm/checkstack`, and sample Postgres manifests in `infra/k8s/postgres.yaml`.

## Quick start (Docker Compose)

```bash
make up
```

Then open `http://localhost:3000` for the dashboard and `http://localhost:8000/healthz` for API health.

The UI calls the API through same-origin `/api` rewrites. Compose wires `INTERNAL_API_URL=http://api:8000` so the browser never needs direct access to port 8000.

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

## Development

```bash
cd services/api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite+pysqlite:///:memory: pytest -q

cd services/web && npm install && npm run dev
```

## License

MIT — see `LICENSE`.
