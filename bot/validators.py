import re

from bot.client import ValidationError

SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,10}USDT$")


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


def validate_quantity(qty: str | float) -> float:
    try:
        parsed = float(qty)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity must be a number, got '{qty}'")
    if parsed <= 0:
        raise ValidationError(f"Quantity must be positive, got {parsed}")
    return parsed


def validate_price(price: str | float | None, order_type: str) -> float | None:
    if order_type == "LIMIT" and price is None:
        raise ValidationError("Price is required for LIMIT orders")
    if price is None:
        return None
    try:
        parsed = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Price must be a number, got '{price}'")
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
    try:
        parsed = float(stop_price)
    except (ValueError, TypeError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'")
    if parsed <= 0:
        raise ValidationError(f"Stop price must be positive, got {parsed}")
    return parsed
