import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import requests

logger = logging.getLogger("bot.client")

RECV_WINDOW = 5000
REQUEST_TIMEOUT = 10
MAX_LOG_BODY = 500


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class BinanceAPIError(TradingBotError):
    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"[{code}] {msg}")


class NetworkError(TradingBotError):
    """Raised when the HTTP transport layer fails."""


class ValidationError(TradingBotError):
    """Raised when user input fails validation."""


class BinanceClient:
    BASE_URL = "https://testnet.binancefuture.com"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    def _sign(self, params: dict) -> dict:
        signed = dict(params)
        signed["timestamp"] = int(time.time() * 1000)
        signed["recvWindow"] = RECV_WINDOW
        query = urlencode(signed)
        signature = hmac.new(
            self._api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        signed["signature"] = signature
        return signed

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": self._api_key}

    def post(self, endpoint: str, params: dict) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        signed_params = self._sign(params)
        safe_params = {k: v for k, v in signed_params.items() if k != "signature"}
        logger.debug("POST %s params=%s", url, safe_params)
        try:
            resp = requests.post(
                url,
                params=signed_params,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("network failure on POST %s: %s", url, exc)
            raise NetworkError(str(exc)) from exc

        logger.debug(
            "response status=%s body=%s",
            resp.status_code,
            resp.text[:MAX_LOG_BODY],
        )
        payload = resp.json()
        if "code" in payload and "msg" in payload:
            raise BinanceAPIError(payload["code"], payload["msg"])
        return payload

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        raw_params = params or {}
        signed_params = self._sign(raw_params)
        safe_params = {k: v for k, v in signed_params.items() if k != "signature"}
        logger.debug("GET %s params=%s", url, safe_params)
        try:
            resp = requests.get(
                url,
                params=signed_params,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("network failure on GET %s: %s", url, exc)
            raise NetworkError(str(exc)) from exc

        logger.debug(
            "response status=%s body=%s",
            resp.status_code,
            resp.text[:MAX_LOG_BODY],
        )
        payload = resp.json()
        if "code" in payload and "msg" in payload:
            raise BinanceAPIError(payload["code"], payload["msg"])
        return payload
