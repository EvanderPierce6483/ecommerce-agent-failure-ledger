from order_failure_service.order_loop import OrderRequest, process_order


class RecordingCapture:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def capture_order_failure(self, **values: object) -> dict[str, object]:
        self.calls.append(values)
        return {"event_id": "evt-test"}


def test_fulfillment_failure_stops_receipt_and_customer_update() -> None:
    recorder = RecordingCapture()
    actions: list[str] = []

    def succeeds(name: str):
        def run(_: OrderRequest) -> None:
            actions.append(name)

        return run

    def inventory_rejected(_: OrderRequest) -> None:
        actions.append("fulfillment")
        raise ValueError("inventory reservation rejected")

    result = process_order(
        OrderRequest("ord-1042", "viewer@example.com", "VIDEO-PACK-01", 1),
        recorder,
        checkout=succeeds("checkout"),
        fulfillment=inventory_rejected,
        receipt_sender=succeeds("receipt"),
        customer_update=succeeds("customer_update"),
    )

    assert result.status == "attention_required"
    assert result.completed_steps == ("checkout",)
    assert result.failed_step == "fulfillment"
    assert actions == ["checkout", "fulfillment"]
    assert recorder.calls[0]["idempotency_key"] == "ord-1042:fulfillment:failure"
