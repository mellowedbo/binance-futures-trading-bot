import hashlib
import hmac
import logging
import time
from unittest.mock import patch

import pytest
import requests
import responses

from bot.client import BinanceAPIError, BinanceClient, NetworkError

TEST_KEY = "test_api_key_123"
TEST_SECRET = "test_api_secret_456"


class TestSigning:
    def test_sign_appends_timestamp_and_signature(self):
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        before = int(time.time() * 1000)
        signed = client._sign({"symbol": "BTCUSDT"})
        after = int(time.time() * 1000)
        assert "timestamp" in signed
        assert before <= signed["timestamp"] <= after
        assert "signature" in signed
        assert "recvWindow" in signed
        assert signed["recvWindow"] == 5000

    def test_signature_matches_manual_hmac(self):
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        params = {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET"}
        signed = client._sign(params)
        from urllib.parse import urlencode
        query = urlencode({k: v for k, v in signed.items() if k != "signature"})
        expected_sig = hmac.new(
            TEST_SECRET.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        assert signed["signature"] == expected_sig


class TestPost:
    @responses.activate
    def test_successful_post_returns_payload(self):
        responses.add(
            responses.POST,
            "https://testnet.binancefuture.com/fapi/v1/order",
            json={"orderId": 999, "status": "NEW"},
            status=200,
        )
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        result = client.post("/fapi/v1/order", {"symbol": "BTCUSDT"})
        assert result["orderId"] == 999

    @responses.activate
    def test_api_error_raises(self):
        responses.add(
            responses.POST,
            "https://testnet.binancefuture.com/fapi/v1/order",
            json={"code": -1121, "msg": "Invalid symbol."},
            status=200,
        )
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        with pytest.raises(BinanceAPIError) as exc_info:
            client.post("/fapi/v1/order", {"symbol": "BAD"})
        assert exc_info.value.code == -1121
        assert "Invalid symbol" in exc_info.value.msg

    @responses.activate
    def test_network_error_on_connection_failure(self):
        responses.add(
            responses.POST,
            "https://testnet.binancefuture.com/fapi/v1/order",
            body=requests.exceptions.ConnectionError("refused"),
        )
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        with pytest.raises(NetworkError):
            client.post("/fapi/v1/order", {"symbol": "BTCUSDT"})


class TestGet:
    @responses.activate
    def test_successful_get_returns_payload(self):
        responses.add(
            responses.GET,
            "https://testnet.binancefuture.com/fapi/v1/account",
            json={"balances": []},
            status=200,
        )
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        result = client.get("/fapi/v1/account")
        assert "balances" in result


class TestSecretNotLogged:
    @responses.activate
    def test_secret_absent_from_log_output(self, caplog):
        responses.add(
            responses.POST,
            "https://testnet.binancefuture.com/fapi/v1/order",
            json={"orderId": 1},
            status=200,
        )
        client = BinanceClient(TEST_KEY, TEST_SECRET)
        with caplog.at_level(logging.DEBUG, logger="bot.client"):
            client.post("/fapi/v1/order", {"symbol": "BTCUSDT"})
        for record in caplog.records:
            assert TEST_SECRET not in record.message
