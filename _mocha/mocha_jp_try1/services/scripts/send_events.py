#!/usr/bin/env python3
"""Send a mixed, out-of-order event stream, then resend the same event IDs.

This script simulates real factory traffic against the FactoryOps platform:

    1. Generate `--count` unique events (both Type-A and Type-B, shuffled).
    2. POST them all to ui-service.
    3. Loop over the same event_ids / payloads and POST them again as duplicates.

That second pass is the idempotency test: the infra must accept the resend
without creating extra rows.

    Type A (order)     -> core -> worker-service -> RDS Proxy -> Aurora
    Type B (operation) -> core -> SQS -> Lambda -> DynamoDB

Usage
-----
    python send_events.py --url http://<ui-endpoint>:8080
    python send_events.py --url http://<ui-endpoint>:8080 --count 100 --read

Only the Python standard library is required.
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib import error, request

OPERATIONS = ("PACK", "SHIP")
OPERATORS = ("op-alice", "op-bob", "operator-carol", "op-dave")


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_event_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def make_type_a(index: int, ts: datetime) -> dict:
    """Order event -> events_orders (Aurora)."""
    return {
        "type": "A",
        "event_id": new_event_id("evt-a"),
        "order_id": f"ORD-{1000 + index}",
        "amount": round(random.uniform(10, 500), 2),
        "ts": iso(ts),
    }


def make_type_b(index: int, ts: datetime) -> dict:
    """Operation event -> events_operations (DynamoDB).

    Field rules enforced downstream:
      order_id starts with ORD- ; operator starts with op-/operator- ;
      operation is PACK or SHIP.
    """
    return {
        "type": "B",
        "event_id": new_event_id("evt-b"),
        "order_id": f"ORD-{2000 + index}",
        "operator": random.choice(OPERATORS),
        "operation": random.choice(OPERATIONS),
        "ts": iso(ts),
    }


def build_unique_events(total: int) -> list[dict]:
    """Build `total` unique events (half Type-A, half Type-B), then shuffle.

    Odd totals get one extra Type-A. Timestamps are sequential; send order is
    shuffled so they arrive out of order.
    """
    n_a = (total + 1) // 2
    n_b = total - n_a
    base = datetime.now(timezone.utc) - timedelta(minutes=max(total, 1))
    events: list[dict] = []
    for i in range(n_a):
        events.append(make_type_a(i, base + timedelta(seconds=i * 30)))
    for i in range(n_b):
        events.append(make_type_b(i, base + timedelta(seconds=i * 30 + 15)))
    random.shuffle(events)
    return events


def post_event(base_url: str, payload: dict, timeout: float) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}/api/events",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Request-Id": new_event_id("req"),
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except error.URLError as e:
        return 0, f"connection error: {e.reason}"


def read_events(base_url: str, timeout: float) -> tuple[int, str]:
    req = request.Request(f"{base_url.rstrip('/')}/api/events", method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except error.URLError as e:
        return 0, f"connection error: {e.reason}"


def send_pass(label: str, events: list[dict], args, duplicate: bool) -> int:
    """POST every event in `events`. Returns the number of failures."""
    failures = 0
    tag = " (DUP)" if duplicate else ""
    print(f"\n=== {label}: {len(events)} events{' (same event_ids)' if duplicate else ''} ===")
    for i, payload in enumerate(events, 1):
        status, body = post_event(args.url, payload, args.timeout)
        ok = 200 <= status < 300
        failures += 0 if ok else 1
        marker = "OK " if ok else "ERR"
        print(f"[{i:>3}/{len(events)}] [{marker}] Type-{payload['type']}{tag} "
              f"event_id={payload['event_id']} ts={payload['ts']} -> HTTP {status}")
        if not ok:
            print(f"          response: {body.strip()}")
        if args.delay:
            time.sleep(args.delay)
    return failures


def run(args) -> int:
    if args.seed is not None:
        random.seed(args.seed)

    unique = build_unique_events(args.count)
    n_a = sum(1 for e in unique if e["type"] == "A")
    n_b = len(unique) - n_a

    print(f"Target ui-service : {args.url}")
    print(f"Pass 1            : {len(unique)} unique events "
          f"({n_a} Type-A, {n_b} Type-B), shuffled / out of order")
    print(f"Pass 2            : the same {len(unique)} event_ids sent again as duplicates")

    failures = 0
    failures += send_pass("pass 1 — unique events", unique, args, duplicate=False)
    failures += send_pass("pass 2 — duplicate resend", unique, args, duplicate=True)

    total_posts = len(unique) * 2
    if args.read:
        print("\n--- Consolidated view (GET /api/events) ---")
        status, body = read_events(args.url, args.timeout)
        print(f"HTTP {status}")
        try:
            print(json.dumps(json.loads(body), indent=2))
        except json.JSONDecodeError:
            print(body)

    print(f"\nDone: {total_posts - failures}/{total_posts} accepted, {failures} failed "
          f"({len(unique)} unique event_ids, each posted twice).")
    return 1 if failures else 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Send N unique Type-A/Type-B events, then resend the same event_ids.")
    p.add_argument("--url", default="http://localhost:8080",
                   help="Base URL of ui-service (default: http://localhost:8080)")
    p.add_argument("--count", type=int, default=100,
                   help="Total unique events to generate, then resend (default: 100)")
    p.add_argument("--delay", type=float, default=0.0,
                   help="Seconds to sleep between sends (default: 0)")
    p.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    p.add_argument("--seed", type=int, help="Random seed for reproducible runs")
    p.add_argument("--read", action="store_true",
                   help="After sending, GET /api/events and print the consolidated view")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
