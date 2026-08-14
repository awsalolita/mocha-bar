# FactoryOps Services (ui-service, core-service, worker-service)

Go implementations of the three application services from the Test Project,
plus a Python script to send Type-A and Type-B events.

> The official Test Project ships a **pre-compiled** server binary and forbids
> using unofficial binaries in the graded environment. These Go services are a
> functional re-implementation for local development, testing, and learning —
> they mirror the documented endpoints, event rules, and data paths.

## Event data paths

```
                 ┌──────────────┐   POST /api/events   ┌──────────────┐
  Python /       │  ui-service  │ ───────────────────▶ │ core-service │
  Browser  ────▶ │  (EC2, EDGE) │ ◀─────────────────── │ (ECS, APP)   │
                 └──────────────┘   GET  /api/events    └──────┬───────┘
                                                               │
                    Type A (sync)                              │  Type B (async)
        ┌──────────────────────────────────────┐              ▼
        ▼                                        │        ┌──────────┐
 ┌───────────────┐   RDS Proxy   ┌──────────┐    │        │   SQS    │ events-b-queue
 │ worker-service│ ───────────▶  │  Aurora  │    │        └────┬─────┘
 │ (ECS, DATA)   │               │ Postgres │    │             ▼
 └───────────────┘               └──────────┘    │        ┌──────────┐   ┌────────────┐
      events_orders                               │        │  Lambda  │ ▶ │  DynamoDB  │
                                                  │        │normalizer│   │events_ops  │
   GET /api/events consolidates ─────────────────┘        └──────────┘   └────────────┘
   Type-A (from worker) + Type-B (from DynamoDB)
```

- **Type A** (order): `core -> worker (validate & save) -> RDS Proxy -> Aurora` (`events_orders`)
- **Type B** (operation): `core -> SQS -> Lambda (validate & normalize) -> DynamoDB` (`events_operations`)

The **Lambda `event-normalizer`** is a separate deployable (not in this Go
module). `core-service` reads DynamoDB directly only to build the consolidated
`GET /api/events` view.

## Layout

```
services/
├── cmd/
│   ├── ui-service/       # EC2 (VPC-EDGE): web UI + entry API, forwards to core
│   │   └── web/index.html
│   ├── core-service/     # ECS app-cluster (VPC-APP): routing + consolidation
│   └── worker-service/   # ECS worker-cluster (VPC-DATA): Aurora persistence
├── internal/
│   ├── event/            # shared envelope + validation/normalization rules
│   └── httpx/            # JSON, health, logging + request-id (traceability)
├── scripts/send_events.py
├── build.sh / build.ps1  # cross-compile to dist/<svc>/main (linux/amd64)
└── go.mod
```

## Endpoints

Every service listens on **:8080** and exposes **`GET /health`** (per the spec).

| Service | Method / Path | Behavior |
|---|---|---|
| ui-service | `GET /` | Event-visualization web UI |
| ui-service | `POST /api/events` | Forwards event to `core.svc.internal` |
| ui-service | `GET /api/events` | Proxies core's consolidated view |
| core-service | `POST /api/events` | Type-A → worker (sync); Type-B → SQS (async) |
| core-service | `GET /api/events` | `{ type_a: [...], type_b: [...], counts }` |
| worker-service | `POST /api/events` | Validate Type-A, idempotent insert to Aurora |
| worker-service | `GET /api/events` | Rows from `events_orders` |

## Event schema

```jsonc
// Type A (order)
{ "type": "A", "event_id": "evt-a-001", "order_id": "ORD-1001",
  "amount": 129.99, "ts": "2026-08-12T10:00:00Z" }

// Type B (operation) — validated downstream:
//   order_id starts with ORD- ; operator starts with op-/operator- ; operation in {PACK,SHIP}
{ "type": "B", "event_id": "evt-b-001", "order_id": "ORD-2001",
  "operator": "op-alice", "operation": "PACK", "ts": "2026-08-12T10:00:00Z" }
```

Idempotency: worker uses `INSERT ... ON CONFLICT (event_id) DO NOTHING`, so
duplicated / out-of-order Type-A events are safely ignored.

## Environment variables

**ui-service**
| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Listen port |
| `CORE_SERVICE_URL` | `http://core.svc.internal:8080` | core-service endpoint |

**core-service**
| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Listen port |
| `WORKER_SERVICE_URL` | `http://worker.svc.internal:8080` | worker endpoint (Type-A sync) |
| `EVENTS_B_QUEUE_URL` | *(required)* | SQS `events-b-queue` URL (Type-B async) |
| `DDB_TABLE` | `events_operations` | DynamoDB table for consolidated read |
| `AWS_REGION` | *(from role)* | Use `us-east-1` |

**worker-service**
| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Listen port |
| `DB_HOST` | `localhost` | **RDS Proxy** endpoint (not Aurora directly) |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `factoryops` | Database name |
| `DB_USER` | `postgres` | |
| `DB_PASSWORD` | *(required)* | Prefer Secrets Manager injection |
| `DB_SSLMODE` | `require` | |

AWS credentials for core-service come from the ECS **task role** (SQS
`SendMessage` on the queue, DynamoDB `Scan` on the table).

## Build

Local (host OS):

```bash
go build ./...
```

Cross-compile static linux/amd64 binaries named `main` for the container image
(x86_64 / Amazon Linux 2023 / Alpine, CGO disabled):

```bash
./build.sh          # or: pwsh ./build.ps1
# => dist/ui-service/main, dist/core-service/main, dist/worker-service/main
```

## Docker

Reuse `dockerfiles/golang-binary/Dockerfile` (it `COPY`s a `main` binary):

```bash
./build.sh
for svc in ui-service core-service worker-service; do
  cp dist/$svc/main dockerfiles/golang-binary/main
  docker build -t $svc:latest -f dockerfiles/golang-binary/Dockerfile dockerfiles/golang-binary
done
```

Push each image to ECR and reference it from the ECS task definitions
(see `aws/ECS/ECS.md`). Register `core` and `worker` in Cloud Map so that
`core.svc.internal` and `worker.svc.internal` resolve across VPCs.

## Run locally

```bash
# worker needs Postgres; the rest need worker/SQS as noted.
DB_HOST=localhost DB_PASSWORD=postgres ./dist/worker-service/main &
EVENTS_B_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/<acct>/events-b-queue \
  WORKER_SERVICE_URL=http://localhost:8082 PORT=8081 ./dist/core-service/main &
CORE_SERVICE_URL=http://localhost:8081 PORT=8080 ./dist/ui-service/main &
```

## Send events (Python, stdlib only)

```bash
python scripts/send_events.py --url http://<ui-endpoint>:8080 --type both --count 5
python scripts/send_events.py --url http://<ui-endpoint>:8080 --type A
python scripts/send_events.py --url http://<ui-endpoint>:8080 --read
```

Open `http://<ui-endpoint>:8080/` in a browser to publish events and watch the
consolidated table update.
