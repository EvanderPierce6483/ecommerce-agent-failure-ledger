"""Run the complete happy-path order workflow without starting HTTP."""

from order_failure_service.infrai_client import InfraiClient
from order_failure_service.order_loop import OrderRequest, process_order


def completed(_: OrderRequest) -> None:
    return None


order = OrderRequest("ord-1042", "viewer@example.com", "VIDEO-PACK-01", 1)
result = process_order(
    order,
    InfraiClient(),
    checkout=completed,
    fulfillment=completed,
    receipt_sender=completed,
    customer_update=completed,
)
print(result)
