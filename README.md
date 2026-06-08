A Python CLI for placing MARKET, LIMIT, and STOP_MARKET orders on the Binance Futures USDT-M Testnet.

## Prerequisites

- Python 3.11 or later
- A Binance Futures Testnet account — sign up at `https://testnet.binancefuture.com`
- API key and secret generated from the testnet dashboard (Account → API Management)

## Installation

```bash
git clone <repo-url> trading_bot && cd trading_bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy the example env file and fill in your testnet credentials:

```bash
cp .env.example .env
```

Edit `.env` so it contains your real keys:

```
BINANCE_TESTNET_API_KEY=abc123...
BINANCE_TESTNET_API_SECRET=def456...
```

We load the `.env` file at CLI startup via `python-dotenv`. The keys are never accepted as CLI flags — environment is the only path, which keeps them out of shell history.

## Usage

Place a market buy:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

Place a limit sell:

```bash
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3200
```

Place a stop-market sell:

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 50000
```

On success you will see two Rich panels — one summarizing the request, one showing the exchange response with order ID, status, executed quantity, and average fill price:

```text
╭─ Order Request ──────────────────────────╮
│ Symbol    : BTCUSDT                       │
│ Side      : BUY                           │
│ Type      : MARKET                        │
│ Quantity  : 0.001                         │
╰───────────────────────────────────────────╯

╭─ Order Result ───────────────────────────╮
│ Order ID     : 3847291038                │
│ Status       : FILLED                    │
│ Executed Qty : 0.001                     │
│ Avg Price    : 67,234.50                 │
╰───────────────────────────────────────────╯
✅ Order placed successfully
```

On failure — for example, omitting the `--price` flag on a LIMIT order — the CLI prints a red validation panel and exits with code 1:

```text
╭─ Validation Error ───────────────────────╮
│ Price is required for LIMIT orders        │
╰───────────────────────────────────────────╯
```

## Web UI

A lightweight browser interface is available as an alternative to the CLI.

Start the server:

```bash
python run_ui.py
```

Open http://127.0.0.1:5000 in a browser. The same `.env` credentials used by the CLI are read automatically.

The UI lets you select a symbol, toggle BUY/SELL, choose an order type, fill in the relevant fields, and submit. Price and stop-price inputs appear and disappear based on the selected order type. Successful orders appear immediately in a recent orders table below the form.

The web server does not need to be restarted when `.env` changes — credentials are read at each request.

## Project layout

| Path | Role |
|---|---|
| `cli.py` | Typer CLI entry point |
| `run_ui.py` | Web UI startup script |
| `ui/app.py` | Flask application factory and API routes |
| `ui/templates/index.html` | Single-page browser interface |
| `bot/client.py` | Binance REST wrapper with HMAC signing |
| `bot/orders.py` | OrderManager — maps intent to API params |
| `bot/validators.py` | Pure input validation, no I/O |
| `bot/logging_config.py` | Rotating file + Rich console handler |
| `tests/` | 62-test pytest suite, no live API calls |

## Running tests

```bash
pytest tests/ -v
```

The suite covers validators (28 tests), the Binance REST client (13 tests), order placement logic (9 tests), and the web UI layer (12 tests) — 62 tests total. All Binance HTTP calls are mocked; no live credentials are needed to run the tests.

To run a single file:

```bash
pytest tests/test_ui.py -v
```

## Logging

All log output goes to `logs/trading_bot.log` (created automatically). The file handler rotates at 5 MB with 3 backups. File logs capture DEBUG-level detail — every outgoing request URL and parameter set, every response status and truncated body, every error with full context. The console handler shows INFO and above using Rich for colorized output.

The API secret is never written to any log line. We redact the `signature` parameter before logging request params.

## Assumptions and known limitations

- Quantity precision is not validated against Binance's LOT_SIZE filter. The exchange will reject the order if the step size is wrong, and the error will surface through the normal API error path.
- Symbol validation uses a regex pattern (`^[A-Z0-9]{2,12}USDT$`) rather than fetching the live exchange info endpoint. This means newly listed pairs outside this pattern may be rejected by the validator even though the exchange would accept them.
- There is no retry logic on transient network failures. A single timeout or connection reset raises `NetworkError` immediately. Retrying with backoff is a deliberate non-goal for this scope.
- The bot only places orders — it does not query balances, open positions, or cancel existing orders. Those are out of scope.
- `recvWindow` is hardcoded at 5000 ms. If the testnet experiences high latency, signed requests may expire before reaching the server.
- STOP_MARKET and other conditional order types (STOP, TAKE_PROFIT_MARKET) are not supported on the Binance Futures Testnet's `/fapi/v1/order` endpoint as of 2026. The testnet returns error `-4120` directing you to use the Algo Order API, which is not available on the testnet. On the production Binance Futures exchange, these order types work through the standard endpoint. The CLI, validators, and tests all support STOP_MARKET — it will function correctly against production or once the testnet re-enables it.

## Order types supported

| Type | Required params | Notes |
|---|---|---|
| MARKET | symbol, side, quantity | Immediate fill at current market price |
| LIMIT | symbol, side, quantity, price | Rests on the book; timeInForce defaults to GTC |
| STOP_MARKET | symbol, side, quantity, stopPrice | Triggers a market order when stopPrice is reached |
