"""Input validation for the trading bot CLI.

Keeping validation separate from both the CLI parsing layer and the API
client layer makes the rules easy to unit test and reuse (e.g. from a
future web UI).
"""

import re
from dataclasses import dataclass
from typing import Optional

SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")
VALID_SIDES = {"BUY", "SELL"}
VALID_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


class ValidationError(Exception):
    """Raised when CLI/user input fails validation."""


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None


def validate_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> OrderRequest:
    """Validate raw CLI input and return a normalized OrderRequest.

    Raises ValidationError with a human-readable message on any problem.
    """
    symbol = (symbol or "").strip().upper()
    side = (side or "").strip().upper()
    order_type = (order_type or "").strip().upper()

    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected an uppercase alphanumeric "
            "futures symbol such as BTCUSDT."
        )

    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")

    if order_type not in VALID_TYPES:
        raise ValidationError(f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_TYPES)}.")

    if quantity is None or quantity <= 0:
        raise ValidationError(f"Invalid quantity '{quantity}'. Must be a positive number.")

    if order_type == "LIMIT":
        if price is None or price <= 0:
            raise ValidationError("A positive 'price' is required for LIMIT orders.")

    if order_type == "STOP_MARKET":
        if stop_price is None or stop_price <= 0:
            raise ValidationError("A positive 'stop_price' is required for STOP_MARKET orders.")

    if order_type == "MARKET" and price is not None:
        raise ValidationError("'price' must not be provided for MARKET orders.")

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )
