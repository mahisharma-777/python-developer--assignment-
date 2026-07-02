"""Binance Futures Testnet API client wrapper.

Handles all direct HTTP communication with the Binance Futures Testnet
REST API (USDT-M futures): request signing, timeouts, error translation,
and structured logging of every request/response pair.

A `dry_run` mode is included so the bot (and its logging output) can be
exercised end-to-end without live network access or real credentials —
useful for local development, CI, and for generating sample log files.
Real trading always requires dry_run=False plus valid testnet credentials.
"""

import hashlib
import hmac
import logging
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx / error response."""

    def __init__(self, status_code: int, code: Optional[int], message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error [{status_code}] code={code}: {message}")


class BinanceNetworkError(Exception):
    """Raised when the request to Binance fails at the network/transport level."""


class BinanceFuturesClient:
    """Thin wrapper around the Binance USDT-M Futures Testnet REST API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
        dry_run: bool = False,
    ) -> None:
        if not dry_run and (not api_key or not api_secret):
            raise ValueError("api_key and api_secret must be provided (unless dry_run=True)")

        self.api_key = api_key or "dry-run-key"
        self.api_secret = (api_secret or "dry-run-secret").encode()
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.session = session or requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    # Low level helpers
    # ------------------------------------------------------------------ #
    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query_string.encode(), hashlib.sha256).hexdigest()
        return signature

    def _simulate_response(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a realistic-looking response for dry_run mode."""
        if path == "/fapi/v1/order" and method == "POST":
            qty = float(params.get("quantity", 0))
            price = params.get("price")
            simulated_fill_price = price if price is not None else "50000.00"
            return {
                "orderId": int(time.time() * 1000) % 10_000_000,
                "symbol": params.get("symbol"),
                "status": "FILLED" if params.get("type") == "MARKET" else "NEW",
                "clientOrderId": f"dryrun-{uuid.uuid4().hex[:12]}",
                "price": str(price) if price is not None else "0",
                "avgPrice": str(simulated_fill_price) if params.get("type") == "MARKET" else "0.00000",
                "origQty": str(qty),
                "executedQty": str(qty) if params.get("type") == "MARKET" else "0",
                "type": params.get("type"),
                "side": params.get("side"),
                "timeInForce": params.get("timeInForce", "GTC"),
            }
        if path == "/fapi/v1/ping":
            return {}
        if path == "/fapi/v1/time":
            return {"serverTime": int(time.time() * 1000)}
        return {"dry_run": True, "note": "No simulated response defined for this endpoint."}

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = dict(params or {})
        url = f"{self.base_url}{path}"

        if signed and not self.dry_run:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = RECV_WINDOW_MS
            params["signature"] = self._sign(params)

        log_prefix = "DRY-RUN " if self.dry_run else ""
        logger.info(
            "%sREQUEST method=%s path=%s params=%s",
            log_prefix,
            method,
            path,
            {k: v for k, v in params.items() if k != "signature"},
        )

        if self.dry_run:
            payload = self._simulate_response(method, path, params)
            logger.info("%sRESPONSE method=%s path=%s body=%s", log_prefix, method, path, payload)
            return payload

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params if method == "GET" else None,
                data=params if method != "GET" else None,
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("NETWORK ERROR method=%s path=%s error=%s", method, path, exc)
            raise BinanceNetworkError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.ok:
            logger.info(
                "RESPONSE method=%s path=%s status=%s body=%s", method, path, response.status_code, payload
            )
            return payload

        error_code = payload.get("code") if isinstance(payload, dict) else None
        error_msg = payload.get("msg") if isinstance(payload, dict) else str(payload)
        logger.error(
            "API ERROR method=%s path=%s status=%s code=%s msg=%s",
            method,
            path,
            response.status_code,
            error_code,
            error_msg,
        )
        raise BinanceAPIError(response.status_code, error_code, error_msg or "Unknown error")

    # ------------------------------------------------------------------ #
    # Public (unsigned) endpoints
    # ------------------------------------------------------------------ #
    def ping(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/ping")

    def server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/time")

    def exchange_info(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    # ------------------------------------------------------------------ #
    # Trading endpoints (SIGNED)
    # ------------------------------------------------------------------ #
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        reduce_only: Optional[bool] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = price
            params["timeInForce"] = time_in_force or "GTC"

        if order_type == "STOP_MARKET":
            if stop_price is None:
                raise ValueError("stop_price is required for STOP_MARKET orders")
            params["stopPrice"] = stop_price

        if reduce_only is not None:
            params["reduceOnly"] = "true" if reduce_only else "false"

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def account_balance(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v2/balance", signed=True)
