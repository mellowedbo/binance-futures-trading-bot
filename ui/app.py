import logging
import os

from dotenv import load_dotenv
from flask import Flask, render_template, request

from bot.client import BinanceAPIError, BinanceClient, NetworkError
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
ORDER_TYPES = ["MARKET", "LIMIT", "STOP_MARKET"]

logger = logging.getLogger("bot.ui")


def create_app(api_key: str | None = None, api_secret: str | None = None) -> Flask:
    setup_logging()
    load_dotenv()

    app = Flask(__name__)

    if api_key and api_secret:
        resolved_key = api_key
        resolved_secret = api_secret
    else:
        resolved_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
        resolved_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "")

    creds_missing = (
        not resolved_key
        or not resolved_secret
        or resolved_key.startswith("your_")
        or resolved_secret.startswith("your_")
    )

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html", symbols=SYMBOLS, order_types=ORDER_TYPES
        )

    @app.route("/api/order", methods=["POST"])
    def place_order() -> tuple[dict, int]:
        if creds_missing:
            logger.error("api credentials not configured")
            return {"error": "API credentials not configured."}, 503

        data = request.get_json(silent=True)
        if not data:
            return {"error": "Request body must be valid JSON."}, 400

        try:
            symbol = validate_symbol(data.get("symbol", ""))
            side = validate_side(data.get("side", ""))
            order_type = validate_order_type(data.get("type", ""))
            quantity = validate_quantity(data.get("quantity", 0))
            price = validate_price(data.get("price"), order_type)
            stop_price = validate_stop_price(data.get("stop_price"), order_type)
        except Exception as exc:
            return {"error": str(exc)}, 400

        logger.info(
            "web order request: %s %s %s qty=%s", order_type, side, symbol, quantity
        )

        client = BinanceClient(resolved_key, resolved_secret)
        manager = OrderManager(client)

        try:
            if order_type == "MARKET":
                resp = manager.place_market_order(symbol, side, quantity)
            elif order_type == "LIMIT":
                resp = manager.place_limit_order(symbol, side, quantity, price)
            else:
                resp = manager.place_stop_market_order(
                    symbol, side, quantity, stop_price
                )
        except BinanceAPIError as exc:
            logger.error("web order rejected: [%s] %s", exc.code, exc.msg)
            return {"error": f"[{exc.code}] {exc.msg}"}, 502
        except NetworkError as exc:
            logger.error("web order network failure: %s", exc)
            return {"error": "Could not reach Binance testnet. Check connectivity."}, 503

        logger.info(
            "web order placed: orderId=%s status=%s",
            resp.get("orderId"),
            resp.get("status"),
        )
        return resp, 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
