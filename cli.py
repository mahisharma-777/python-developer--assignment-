"""Command line entry point for the Binance Futures Testnet trading bot.

Usage examples:

    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    python cli.py --symbol BTCUSDT --side SELL --type LIMIT \\
        --quantity 0.01 --price 45000

    python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET \\
        --quantity 0.01 --stop-price 44000

Credentials are read from the BINANCE_API_KEY / BINANCE_API_SECRET
environment variables. Pass --dry-run to exercise the full request/
response/logging pipeline without hitting the network or needing real
credentials (useful for testing).
"""

import argparse
import logging
import os
import sys

from bot.client import DEFAULT_BASE_URL, BinanceFuturesClient
from bot.logging_config import setup_logging
from bot.orders import OrderExecutionError, place_order
from bot.validators import ValidationError, validate_order_request

logger = logging.getLogger("trading_bot.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Simplified trading bot for Binance USDT-M Futures Testnet.",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order side",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, type=float, help="Order quantity")
    parser.add_argument("--price", type=float, default=None, help="Limit price (required for LIMIT orders)")
    parser.add_argument(
        "--stop-price",
        dest="stop_price",
        type=float,
        default=None,
        help="Stop trigger price (required for STOP_MARKET orders)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BINANCE_FUTURES_BASE_URL", DEFAULT_BASE_URL),
        help="API base URL (defaults to the Futures Testnet)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the request/response cycle locally without calling the real API",
    )
    return parser


def main(argv=None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        req = validate_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        print(f"INVALID INPUT: {exc}")
        logger.warning("Validation failed: %s", exc)
        return 2

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if not args.dry_run and (not api_key or not api_secret):
        print(
            "Missing API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
            "environment variables (see README.md), or pass --dry-run to test "
            "without live credentials."
        )
        logger.error("Missing API credentials in environment.")
        return 2

    try:
        client = BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=args.base_url,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"INVALID CONFIGURATION: {exc}")
        return 2

    if args.dry_run:
        print("[DRY-RUN MODE — no real orders will be sent]")

    try:
        place_order(client, req)
    except OrderExecutionError:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
