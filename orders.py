"""Order placement orchestration: ties the validators and API client together
and handles all user-facing output for order requests/responses."""

import logging
from typing import Any, Dict

from .client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from .validators import OrderRequest

logger = logging.getLogger("trading_bot.orders")


class OrderExecutionError(Exception):
    """Raised when an order could not be placed, wrapping the root cause."""


def print_order_summary(req: OrderRequest) -> None:
    print("=" * 50)
    print("ORDER REQUEST SUMMARY")
    print("=" * 50)
    print(f"Symbol      : {req.symbol}")
    print(f"Side        : {req.side}")
    print(f"Type        : {req.order_type}")
    print(f"Quantity    : {req.quantity}")
    if req.price is not None:
        print(f"Price       : {req.price}")
    if req.stop_price is not None:
        print(f"Stop Price  : {req.stop_price}")
    print("=" * 50)


def print_order_response(response: Dict[str, Any]) -> None:
    print("-" * 50)
    print("ORDER RESPONSE")
    print("-" * 50)
    print(f"Order ID     : {response.get('orderId')}")
    print(f"Status       : {response.get('status')}")
    print(f"Executed Qty : {response.get('executedQty')}")
    avg_price = response.get("avgPrice")
    if avg_price is not None:
        print(f"Avg Price    : {avg_price}")
    print(f"Client OrdID : {response.get('clientOrderId')}")
    print("-" * 50)


def place_order(client: BinanceFuturesClient, req: OrderRequest) -> Dict[str, Any]:
    """Validate-then-place workflow. Prints a summary, submits the order,
    prints the response, and logs every step. Raises OrderExecutionError
    on any API or network failure (already logged and printed)."""
    print_order_summary(req)
    logger.info(
        "Submitting order symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        req.symbol,
        req.side,
        req.order_type,
        req.quantity,
        req.price,
        req.stop_price,
    )

    try:
        response = client.place_order(
            symbol=req.symbol,
            side=req.side,
            order_type=req.order_type,
            quantity=req.quantity,
            price=req.price,
            stop_price=req.stop_price,
        )
    except BinanceAPIError as exc:
        logger.error("Order rejected by API: %s", exc)
        print(f"FAILED: Binance API rejected the order -> {exc.message} (code={exc.code})")
        raise OrderExecutionError(str(exc)) from exc
    except BinanceNetworkError as exc:
        logger.error("Network failure while placing order: %s", exc)
        print(f"FAILED: Network error while contacting Binance -> {exc}")
        raise OrderExecutionError(str(exc)) from exc

    print_order_response(response)
    print(f"SUCCESS: Order placed for {req.symbol} ({req.side} {req.order_type}).")
    logger.info("Order placed successfully: %s", response)
    return response
