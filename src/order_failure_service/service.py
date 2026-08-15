"""Runnable HTTP boundary for the order agent."""

from __future__ import annotations

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .infrai_client import InfraiClient, InfraiError
from .order_loop import OrderRequest, process_order


def checkout(_: OrderRequest) -> None:
    return None


def fulfillment(_: OrderRequest) -> None:
    return None


def receipt_sender(_: OrderRequest) -> None:
    return None


def customer_update(_: OrderRequest) -> None:
    return None


class OrderHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/orders/process":
            self._send(404, {"error": "route not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            order = OrderRequest.from_dict(json.loads(self.rfile.read(length)))
            result = process_order(
                order,
                InfraiClient(),
                checkout=checkout,
                fulfillment=fulfillment,
                receipt_sender=receipt_sender,
                customer_update=customer_update,
            )
            self._send(200, asdict(result))
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except InfraiError as exc:
            status = exc.status_code if 400 <= exc.status_code < 500 else 502
            self._send(status, {"error": exc.code, "detail": exc.detail})

    def _send(self, status: int, body: dict[str, object]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8080), OrderHandler)
    print("order failure service listening on http://127.0.0.1:8080")
    server.serve_forever()


if __name__ == "__main__":
    main()
