import pytest
from unittest.mock import MagicMock

from bot.client import BinanceAPIError, NetworkError
from ui.app import create_app


FAKE_KEY = "test_key_ui"
FAKE_SECRET = "test_secret_ui"
SUCCESS_RESPONSE = {
    "orderId": 9999,
    "status": "NEW",
    "executedQty": "0.01",
    "avgPrice": "0",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
}


@pytest.fixture
def client():
    app = create_app(api_key=FAKE_KEY, api_secret=FAKE_SECRET)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def mock_post(monkeypatch):
    m = MagicMock(return_value=SUCCESS_RESPONSE)
    monkeypatch.setattr("bot.client.BinanceClient.post", m)
    return m


class TestIndexRoute:
    def test_get_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_get_index_contains_form_elements(self, client):
        resp = client.get("/")
        assert b"BTCUSDT" in resp.data

    def test_get_index_contains_order_type_select(self, client):
        resp = client.get("/")
        assert b"MARKET" in resp.data


class TestOrderApiValidation:
    def test_missing_symbol_returns_400(self, client):
        resp = client.post(
            "/api/order",
            json={"side": "BUY", "type": "MARKET", "quantity": "0.01"},
        )
        assert resp.status_code == 400
        assert "error" in resp.json

    def test_invalid_side_returns_400(self, client):
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "HOLD", "type": "MARKET", "quantity": "0.01"},
        )
        assert resp.status_code == 400
        assert "error" in resp.json

    def test_missing_price_for_limit_returns_400(self, client):
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": "0.01"},
        )
        assert resp.status_code == 400
        assert "error" in resp.json

    def test_zero_quantity_returns_400(self, client):
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0"},
        )
        assert resp.status_code == 400
        assert "error" in resp.json

    def test_missing_stop_price_for_stop_market_returns_400(self, client):
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "SELL", "type": "STOP_MARKET", "quantity": "0.01"},
        )
        assert resp.status_code == 400
        assert "error" in resp.json


class TestOrderApiSuccess:
    def test_market_order_returns_200_with_order_id(self, client, mock_post):
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.01"},
        )
        assert resp.status_code == 200
        assert resp.json["orderId"] == 9999

    def test_limit_order_returns_200_with_order_id(self, client, mock_post):
        resp = client.post(
            "/api/order",
            json={
                "symbol": "ETHUSDT",
                "side": "SELL",
                "type": "LIMIT",
                "quantity": "0.1",
                "price": "3200",
            },
        )
        assert resp.status_code == 200
        assert resp.json["orderId"] == 9999


class TestOrderApiErrors:
    def test_binance_api_error_returns_502(self, client, monkeypatch):
        def raise_api_error(self, endpoint, params):
            raise BinanceAPIError(-1121, "Invalid symbol.")

        monkeypatch.setattr("bot.client.BinanceClient.post", raise_api_error)
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.01"},
        )
        assert resp.status_code == 502
        assert b"-1121" in resp.data

    def test_network_error_returns_503(self, client, monkeypatch):
        def raise_network_error(self, endpoint, params):
            raise NetworkError("refused")

        monkeypatch.setattr("bot.client.BinanceClient.post", raise_network_error)
        resp = client.post(
            "/api/order",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.01"},
        )
        assert resp.status_code == 503
