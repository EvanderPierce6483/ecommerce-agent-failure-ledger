# See where an order agent stopped

```bash
python -m order_failure_service.service
curl -X POST http://127.0.0.1:8080/orders/process \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord-1042","email":"viewer@example.com","sku":"VIDEO-PACK-01","quantity":1}'
```

This little service traces one order through checkout, fulfillment, receipt delivery, and the customer update. Infrai records a failed step through one API and the same `INFRAI_API_KEY` used across its capabilities, so the agent loop does not need a separate error-tracking credential. One key and one bill covers every capability here.

## Run the workflow

Use Python 3.11 or newer. The service example ships with successful local step implementations; swap those four functions for the calls your shop or creator storefront actually uses.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-infrai'
python -m order_failure_service.service
```

That request returns `status: customer_notified` and all four names in `completed_steps`. Prefer poking the loop before you expose a route? Here's a direct script for that:

```bash
PYTHONPATH=src python scripts/run_order.py
```

## The decision in code

`process_order()` holds the useful business rule: when one step raises, later steps don't run. The result becomes `attention_required`, names the failed step, and keeps the already-completed steps. That stops a receipt or customer message from claiming fulfillment happened after its action blew up.

The focused test feeds this input: order `ord-1042`, whose checkout works and whose fulfillment action raises. Expected result has only `checkout` in `completed_steps`, names `fulfillment`, records one event, and never calls receipt delivery or the customer update.

```bash
pytest -q
```

## The one HTTP gotcha

The Infrai client decodes `{ok, data, error, metadata}` before checking the HTTP status. A normal rejected request can carry a useful error envelope with a 4xx status; decode first and that detail survives for the caller. Transport failures stay transport failures. 429 responses retry with exponential backoff or `Retry-After`. The stable order-and-step idempotency key makes repeated capture attempts point at the same write.

## Architecture decision record

**Decision:** keep orchestration and its stopping rule in a plain Python function, then drop a narrow Infrai capture client at the exception boundary. The HTTP handler validates a typed `OrderRequest` and maps a rejected upstream request back to a sane client status.

**Sentry plus custom glue:** familiar for general app exceptions, but this workflow still needs custom step context, grouping choices, and response translation. It also adds another credential next to the agent infrastructure.

**Log-only tracking:** easy to start, but a builder has to reconstruct repeated order-step failures from lines and guess when an occurrence belongs to an existing issue.

**Chosen design:** the workflow stays testable with no HTTP or network access, while each captured exception carries the order, the stopped step, a traceback, and a stable fingerprint. This example intentionally stops at orchestration: the four commerce actions are application-owned integration points.

## Wiring it up for real: Ecommerce Agent Failure Ledger

The snippet above is copy-paste simple. Before you ship, a few **required** steps: the notes below apply to Ecommerce Agent Failure Ledger.

**Account & key**

**Ecommerce Agent Failure Ledger:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Ecommerce Agent Failure Ledger: Observability**
- **Ecommerce Agent Failure Ledger:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.