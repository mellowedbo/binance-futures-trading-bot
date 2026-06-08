import logging

from bot.client import BinanceClient

logger = logging.getLogger("bot.orders")

ORDER_ENDPOINT = "/fapi/v1/order"


class OrderManager:
    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
        }
        logger.info(
            "sending MARKET %s %s qty=%.6f", side, symbol, quantity
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
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": time_in_force,
        }
        logger.info(
            "sending LIMIT %s %s qty=%.6f price=%.2f tif=%s",
            side, symbol, quantity, price, time_in_force,
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
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": quantity,
            "stopPrice": stop_price,
        }
        logger.info(
            "sending STOP_MARKET %s %s qty=%.6f stopPrice=%.2f",
            side, symbol, quantity, stop_price,
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
