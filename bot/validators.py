import math
import re

from bot.client import ValidationError

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,12}USDT$")

# Binance quantity/price fields must be plain decimal strings — floats such as
# 0.00001 serialise as "1e-05" via urlencode and the exchange rejects them.
_MAX_DECIMALS = 10


def format_number(value: float) -> str:
    """Serialise a float as a plain decimal string (never scientific notation).

    ``0.00001`` -> ``"0.00001"``, ``10.0`` -> ``"10"``, ``3200.0`` -> ``"3200"``.
    Raises :class:`ValidationError` for NaN/inf so they can never reach the API.
    """
    if isinstance(value, str):
        raise TypeError("format_number expects a float; validate/parse strings first")
    if not math.isfinite(value):
        raise ValidationError(f"Numeric value must be finite, got {value}")
    text = f"{value:.{_MAX_DECIMALS}f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def validate_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise ValidationError("Symbol cannot be empty")
    if not SYMBOL_PATTERN.match(cleaned):
        raise ValidationError(
            f"Symbol '{symbol}' is invalid — expected format like BTCUSDT or ETHUSDT"
        )
    return cleaned


def validate_side(side: str) -> str:
    normalised = side.strip().upper()
    if normalised not in ("BUY", "SELL"):
        raise ValidationError(
            f"Side must be BUY or SELL, got '{side}'"
        )
    return normalised


def validate_order_type(order_type: str) -> str:
    normalised = order_type.strip().upper()
    if normalised not in ("MARKET", "LIMIT", "STOP_MARKET"):
        raise ValidationError(
            f"Order type must be MARKET, LIMIT, or STOP_MARKET, got '{order_type}'"
        )
    return normalised


def _parse_finite(value: str | float, label: str) -> float:
    try:
        parsed = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{label} must be a number, got '{value}'")
    if not math.isfinite(parsed):
        raise ValidationError(f"{label} must be a finite number, got {parsed}")
    return parsed


def validate_quantity(qty: str | float) -> float:
    parsed = _parse_finite(qty, "Quantity")
    if parsed <= 0:
        raise ValidationError(f"Quantity must be positive, got {parsed}")
    return parsed


def validate_price(price: str | float | None, order_type: str) -> float | None:
    if order_type == "LIMIT" and price is None:
        raise ValidationError("Price is required for LIMIT orders")
    if price is None:
        return None
    parsed = _parse_finite(price, "Price")
    if parsed <= 0:
        raise ValidationError(f"Price must be positive, got {parsed}")
    return parsed


def validate_stop_price(
    stop_price: str | float | None, order_type: str
) -> float | None:
    if order_type == "STOP_MARKET" and stop_price is None:
        raise ValidationError("Stop price is required for STOP_MARKET orders")
    if stop_price is None:
        return None
    parsed = _parse_finite(stop_price, "Stop price")
    if parsed <= 0:
        raise ValidationError(f"Stop price must be positive, got {parsed}")
    return parsed
