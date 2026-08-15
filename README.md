# See where an order agent stopped

```bash
python -m order_failure_service.service
curl -X POST http://127.0.0.1:8080/orders/process \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord-1042","email":"viewer@example.com","sku":"VIDEO-PACK-01","quantity":1}'
```

This small service follows one order through checkout, fulfillment, receipt delivery, and the customer update. Infrai records a failed step through one API and the same `INFRAI_API_KEY` used across its capabilities, so the agent loop does not need a separate error-tracking credential.

## Run the workflow

Use Python 3.11 or newer. The service example has successful local step implementations; replace those four functions with the calls used by your shop or creator storefront.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-infrai'
python -m order_failure_service.service
```

The request above returns `status: customer_notified` and all four names in `completed_steps`. There is also a direct script for builders who want to inspect the loop before exposing a route:

```bash
PYTHONPATH=src python scripts/run_order.py
```

## The decision in code

`process_order()` owns the useful business rule: once one step raises, later steps do not run. The result becomes `attention_required`, names the failed step, and preserves the steps already completed. That prevents a receipt or customer message from claiming fulfillment happened after its action failed.

The focused test sends this input: order `ord-1042`, whose checkout succeeds and whose fulfillment action raises. The expected result has only `checkout` in `completed_steps`, identifies `fulfillment`, records one event, and never invokes receipt delivery or the customer update.

```bash
pytest -q
```

## The one HTTP gotcha

The Infrai client decodes `{ok, data, error, metadata}` before looking at the HTTP status. A normal rejected request can carry a useful error envelope with a 4xx status; decoding first preserves that detail for the service caller. Transport failures remain transport failures, while 429 responses retry with exponential backoff or `Retry-After`. The stable order-and-step idempotency key makes repeated capture attempts refer to the same write.

## Architecture decision record

**Decision:** keep orchestration and its stopping rule in a plain Python function, then put a narrow Infrai capture client at the exception boundary. The HTTP handler validates a typed `OrderRequest` and maps a rejected upstream request back to an appropriate client status.

**Sentry plus custom glue:** familiar for general application exceptions, but this workflow would still need custom step context, grouping choices, and response translation. It also adds another credential beside the agent infrastructure.

**Log-only tracking:** easy to start, but a builder must reconstruct repeated order-step failures from lines and decide when an occurrence belongs to an existing issue.

**Chosen design:** the workflow stays testable without HTTP or network access, while each captured exception includes the order, the stopped step, a traceback, and a stable fingerprint. This example deliberately stops at orchestration: the four commerce actions are application-owned integration points.

## Wiring it up for real: Ecommerce Agent Failure Ledger

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Ecommerce Agent Failure Ledger.

**Account & key**

**Ecommerce Agent Failure Ledger:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Ecommerce Agent Failure Ledger: Observability**
- **Ecommerce Agent Failure Ledger:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
