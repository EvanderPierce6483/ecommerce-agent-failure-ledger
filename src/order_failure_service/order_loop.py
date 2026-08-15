"""Business decisions for a checkout-to-customer-update agent loop."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    email: str
    sku: str
    quantity: int

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "OrderRequest":
        order_id = value.get("order_id")
        email = value.get("email")
        sku = value.get("sku")
        quantity = value.get("quantity")
        if not isinstance(order_id, str) or not order_id:
            raise ValueError("order_id must be a non-empty string")
        if not isinstance(email, str) or "@" not in email:
            raise ValueError("email must be valid")
        if not isinstance(sku, str) or not sku:
            raise ValueError("sku must be a non-empty string")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        return cls(order_id, email, sku, quantity)


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    status: str
    completed_steps: tuple[str, ...]
    failed_step: str | None = None


class FailureRecorder(Protocol):
    def capture_order_failure(
        self, *, order_id: str, step: str, exception: str, idempotency_key: str
    ) -> dict[str, object]:
        """Record one stopped order step."""


Step = Callable[[OrderRequest], None]


def process_order(
    order: OrderRequest,
    recorder: FailureRecorder,
    *,
    checkout: Step,
    fulfillment: Step,
    receipt_sender: Step,
    customer_update: Step,
) -> OrderResult:
    steps = (
        ("checkout", checkout),
        ("fulfillment", fulfillment),
        ("receipt", receipt_sender),
        ("customer_update", customer_update),
    )
    completed: list[str] = []
    for step_name, action in steps:
        try:
            action(order)
        except Exception as exc:
            recorder.capture_order_failure(
                order_id=order.order_id,
                step=step_name,
                exception="".join(traceback.format_exception(exc)),
                idempotency_key=f"{order.order_id}:{step_name}:failure",
            )
            return OrderResult(order.order_id, "attention_required", tuple(completed), step_name)
        completed.append(step_name)
    return OrderResult(order.order_id, "customer_notified", tuple(completed))
