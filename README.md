# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application for placing MARKET, LIMIT, and
STOP_MARKET orders on the Binance USDT-M Futures Testnet, with input
validation, structured logging, and clean error handling.

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance REST API client wrapper (signing, requests, error handling)
    orders.py           # Order placement orchestration + user-facing output
    validators.py        # CLI input validation
    logging_config.py    # Rotating file + console logging setup
  cli.py                 # CLI entry point (argparse)
  logs/
    trading_bot.log      # Generated log file (see "Sample log output" below)
  README.md
  requirements.txt
```

The API layer (`bot/client.py`) is fully decoupled from the CLI layer
(`cli.py`): the client only knows how to talk to Binance; the CLI only
knows how to parse args and orchestrate validation + calls. This makes it
straightforward to reuse `bot/` behind a different interface later (a web
UI, a scheduler, etc.).

## 1. Setup

### 1.1 Create a Binance Futures Testnet account & API key

1. Go to https://testnet.binancefuture.com and register/log in (you can
   sign in with a GitHub account).
2. Once logged in, generate an API Key + Secret from the testnet site
   (there's an "API Key" panel on the dashboard).
3. The testnet gives you a free balance of mock USDT to trade with — no
   real funds are ever involved.

### 1.2 Install dependencies

Requires Python 3.9+.

```bash
cd trading_bot
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

### 1.3 Configure credentials

The bot reads credentials from environment variables (never hard-code
secrets in source):

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

On Windows (PowerShell):

```powershell
$env:BINANCE_API_KEY="your_testnet_api_key"
$env:BINANCE_API_SECRET="your_testnet_api_secret"
```

By default the bot targets `https://testnet.binancefuture.com`. Override
with `--base-url` or `BINANCE_FUTURES_BASE_URL` if needed.

## 2. Usage

### Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 45000
```

### Stop-Market order (bonus third order type)

```bash
python cli.py --symbol ETHUSDT --side BUY --type STOP_MARKET --quantity 0.1 --stop-price 2500
```

### CLI arguments

| Flag           | Required          | Notes                                    |
|----------------|--------------------|-------------------------------------------|
| `--symbol`     | yes                | e.g. `BTCUSDT`                            |
| `--side`       | yes                | `BUY` or `SELL`                           |
| `--type`       | yes                | `MARKET`, `LIMIT`, or `STOP_MARKET`       |
| `--quantity`   | yes                | positive float                            |
| `--price`      | yes, for LIMIT     | positive float                            |
| `--stop-price` | yes, for STOP_MARKET | positive float                          |
| `--base-url`   | no                 | defaults to the Futures Testnet URL       |
| `--dry-run`    | no                 | simulate the call locally, no network/credentials needed |

Every run prints:
1. An order request summary (symbol, side, type, quantity, price/stop price).
2. The order response (orderId, status, executedQty, avgPrice if available).
3. A clear `SUCCESS`/`FAILED` message.

### Try it without credentials (`--dry-run`)

To exercise the whole pipeline (validation → request → response →
logging) without live network access or API keys, add `--dry-run`:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

This is what was used to produce the sample log entries in
`logs/trading_bot.log` included in this submission (see note below).

## 3. Logging

Every request, response, and error is logged to `logs/trading_bot.log`
(rotating, 2 MB per file, 5 backups) and mirrored to the console. Log
format:

```
<timestamp> | <LEVEL> | <logger name> | <message>
```

`logs/trading_bot.log` in this repo already contains sample output from:
- one MARKET order (dry-run)
- one LIMIT order (dry-run)
- one STOP_MARKET order (dry-run, bonus order type)
- a rejected/invalid input example (validation error path)
- a real network call attempt against the live testnet URL, demonstrating
  the API/network error-handling path

## 4. Error handling

- **Invalid input** — caught in `bot/validators.py` before any network
  call is made (bad symbol format, invalid side/type, non-positive
  quantity, missing price/stop-price where required). Reported as
  `INVALID INPUT: ...` and logged as a warning.
- **API errors** (e.g. bad symbol, insufficient balance, invalid
  timestamp) — caught in `bot/client.py`, raised as `BinanceAPIError`,
  reported as `FAILED: Binance API rejected the order -> ...` and logged
  as an error with the HTTP status/code/message from Binance.
- **Network failures** (timeouts, DNS, connection errors) — caught as
  `BinanceNetworkError`, reported and logged similarly.

## 5. Assumptions

- Only USDT-M Futures Testnet (`/fapi/v1/...`) is targeted — Coin-M
  futures and Spot Testnet are out of scope.
- LIMIT orders default to `GTC` (Good-Til-Cancelled) time-in-force since
  the task didn't specify one.
- Direct REST calls (`requests` + HMAC-SHA256 signing) were used instead
  of `python-binance`, to keep the dependency footprint minimal and make
  the request/response/signing logic fully transparent and testable —
  the task allowed either approach.
- `--dry-run` mode was added so the bot's full logging pipeline could be
  demonstrated and submitted without embedding real API credentials in
  this repository; running without `--dry-run` and with real
  `BINANCE_API_KEY`/`BINANCE_API_SECRET` env vars set sends real
  (testnet) orders.
- `STOP_MARKET` was chosen as the bonus third order type since it's a
  single extra endpoint parameter (`stopPrice`) on the same `/fapi/v1/order`
  endpoint already used by MARKET/LIMIT.

## 6. Possible next steps (not implemented)

- OCO / TWAP / Grid order types.
- Order status polling / websocket user-data-stream integration.
- Unit tests with a mocked `requests.Session`.
