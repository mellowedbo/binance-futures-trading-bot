import logging
import uuid

from bot.client import BinanceClient
from bot.validators import format_number

logger = logging.getLogger("bot.orders")

ORDER_ENDPOINT = "/fapi/v1/order"


def _client_order_id(explicit: str | None) -> str:
    """Use the caller's id when given, else generate one for idempotency.

    A client order id means a timed-out request can never be blindly retried
    into a duplicate position — the exchange dedupes on the id.
    """
    return explicit if explicit else uuid.uuid4().hex[:32]


class OrderManager:
    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    # ------------------------------------------------------------------ #
    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str | None = None,
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": format_number(quantity),
            "newClientOrderId": _client_order_id(client_order_id),
        }
        logger.info(
            "sending MARKET %s %s qty=%s", side, symbol, params["quantity"]
        )
        resp = self._client.post(ORDER_ENDPOINT, params)
        logger.info(
            "order %s status=%s executedQty=%s avgPrice=%s",
            resp.get("orderId"),
            resp.get("status"),
            resp.get("executedQty"),
            resp.get("avgPrice", "n/a"),
        )
        return resp

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
        client_order_id: str | None = None,
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": format_number(quantity),
            "price": format_number(price),
            "timeInForce": time_in_force,
            "newClientOrderId": _client_order_id(client_order_id),
        }
        logger.info(
            "sending LIMIT %s %s qty=%s price=%s tif=%s",
            side, symbol, params["quantity"], params["price"], time_in_force,
        )
        resp = self._client.post(ORDER_ENDPOINT, params)
        logger.info(
            "order %s status=%s executedQty=%s avgPrice=%s",
            resp.get("orderId"),
            resp.get("status"),
            resp.get("executedQty"),
            resp.get("avgPrice", "n/a"),
        )
        return resp

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        reduce_only: bool = False,
        client_order_id: str | None = None,
    ) -> dict:
        """Place a STOP_MARKET order.

        ``reduce_only=True`` marks the order as *closing* — it can only ever
        reduce an existing position, never open a new one. Always use this for
        stop-losses: a plain STOP_MARKET with the wrong side will silently
        OPEN a new position instead of protecting the old one.
        """
        params: dict = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": format_number(quantity),
            "stopPrice": format_number(stop_price),
            "newClientOrderId": _client_order_id(client_order_id),
        }
        if reduce_only:
            params["reduceOnly"] = "true"
        logger.info(
            "sending STOP_MARKET %s %s qty=%s stopPrice=%s reduceOnly=%s",
            side, symbol, params["quantity"], params["stopPrice"], reduce_only,
        )
        resp = self._client.post(ORDER_ENDPOINT, params)
        logger.info(
            "order %s status=%s executedQty=%s avgPrice=%s",
            resp.get("orderId"),
            resp.get("status"),
            resp.get("executedQty"),
            resp.get("avgPrice", "n/a"),
        )
        return resp
