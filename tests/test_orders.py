from unittest.mock import MagicMock

from bot.client import BinanceClient
from bot.orders import OrderManager


def _make_client_with_mock() -> tuple[BinanceClient, MagicMock]:
    client = BinanceClient("key", "secret")
    mock_post = MagicMock(return_value={
        "orderId": 4242,
        "status": "NEW",
        "executedQty": "0.01",
        "avgPrice": "65000.00",
    })
    client.post = mock_post
    return client, mock_post


class TestPlaceMarketOrder:
    def test_sends_correct_params(self):
        client, mock_post = _make_client_with_mock()
        mgr = OrderManager(client)
        result = mgr.place_market_order("BTCUSDT", "BUY", 0.01)
        mock_post.assert_called_once()
        _, params = mock_post.call_args[0]
        assert params["type"] == "MARKET"
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "BUY"
        assert params["quantity"] == 0.01
        assert "price" not in params
        assert result["orderId"] == 4242


class TestPlaceLimitOrder:
    def test_sends_correct_params(self):
        client, mock_post = _make_client_with_mock()
        mgr = OrderManager(client)
        result = mgr.place_limit_order("ETHUSDT", "SELL", 0.1, 3200.0)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        _, params = call_args[0]
        assert params["type"] == "LIMIT"
        assert params["symbol"] == "ETHUSDT"
        assert params["side"] == "SELL"
        assert params["quantity"] == 0.1
        assert params["price"] == 3200.0
        assert params["timeInForce"] == "GTC"
        assert result["orderId"] == 4242

    def test_custom_time_in_force(self):
        client, mock_post = _make_client_with_mock()
        mgr = OrderManager(client)
        mgr.place_limit_order("ETHUSDT", "BUY", 0.5, 1500.0, time_in_force="IOC")
        _, params = mock_post.call_args[0]
        assert params["timeInForce"] == "IOC"


class TestPlaceStopMarketOrder:
    def test_sends_correct_params(self):
        client, mock_post = _make_client_with_mock()
        mgr = OrderManager(client)
        result = mgr.place_stop_market_order("BTCUSDT", "SELL", 0.01, 58000.0)
        mock_post.assert_called_once()
        _, params = mock_post.call_args[0]
        assert params["type"] == "STOP_MARKET"
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "SELL"
        assert params["quantity"] == 0.01
        assert params["stopPrice"] == 58000.0
        assert "price" not in params
        assert result["orderId"] == 4242
