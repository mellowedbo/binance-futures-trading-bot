import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import requests
from requests.exceptions import JSONDecodeError

logger = logging.getLogger("bot.client")

RECV_WINDOW = 5000
REQUEST_TIMEOUT = 10
MAX_LOG_BODY = 500

# HTTP statuses that indicate rate limiting / IP banning
RATE_LIMIT_STATUSES = {429, 418}


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class BinanceAPIError(TradingBotError):
    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"[{code}] {msg}")


class NetworkError(TradingBotError):
    """Raised when the HTTP transport layer fails."""


class BadResponseError(TradingBotError):
    """Raised when the server returns a body that is not valid JSON."""


class RateLimitError(TradingBotError):
    """Raised on HTTP 429/418 — the exchange is throttling or banning us."""

    def __init__(self, status_code: int, retry_after: int | None = None) -> None:
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited (HTTP {status_code})"
            + (f" — retry after {retry_after}s" if retry_after else "")
        )


class ValidationError(TradingBotError):
    """Raised when user input fails validation."""


class BinanceClient:
    BASE_URL = "https://testnet.binancefuture.com"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    def _request(self, method: str, endpoint: str, params: dict) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        signed_params = self._sign(params)
        safe_params = {k: v for k, v in signed_params.items() if k != "signature"}
        logger.debug("%s %s params=%s", method, url, safe_params)

        try:
            resp = requests.request(
                method,
                url,
                params=signed_params,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("network failure on %s %s: %s", method, url, exc)
            raise NetworkError(str(exc)) from exc

        logger.debug(
            "response status=%s body=%s",
            resp.status_code,
            resp.text[:MAX_LOG_BODY],
        )

        if resp.status_code in RATE_LIMIT_STATUSES:
            retry_after = resp.headers.get("retry-after")
            raise RateLimitError(
                resp.status_code, int(retry_after) if retry_after else None
            )

        try:
            payload = resp.json()
        except (JSONDecodeError, ValueError) as exc:
            logger.error("non-JSON response on %s %s (HTTP %s)", method, url, resp.status_code)
            raise BadResponseError(
                f"Expected JSON from {endpoint} (HTTP {resp.status_code}), "
                f"got: {resp.text[:MAX_LOG_BODY]!r}"
            ) from exc

        # Binance reports failures either via HTTP status or via a body that
        # carries an error code. Success bodies on some endpoints carry
        # {"code": 200, "msg": "success"} — only non-200 codes are errors.
        body_code = payload.get("code") if isinstance(payload, dict) else None
        body_msg = payload.get("msg") if isinstance(payload, dict) else None
        if resp.status_code >= 400 or (body_code is not None and body_code != 200):
            raise BinanceAPIError(int(body_code if body_code is not None else resp.status_code),
                                  str(body_msg or resp.reason))

        return payload

    # ------------------------------------------------------------------ #
    def post(self, endpoint: str, params: dict) -> dict:
        return self._request("POST", endpoint, params)

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        return self._request("GET", endpoint, params or {})
