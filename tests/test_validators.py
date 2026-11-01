import pytest

from bot.client import ValidationError
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)


class TestValidateSymbol:
    def test_valid_symbol_uppercases(self):
        assert validate_symbol("btcusdt") == "BTCUSDT"

    def test_valid_symbol_strips_whitespace(self):
        assert validate_symbol("  ETHUSDT  ") == "ETHUSDT"

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_symbol("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_symbol("   ")

    def test_non_usdt_pair_raises(self):
        with pytest.raises(ValidationError, match="invalid"):
            validate_symbol("BTCBUSD")


class TestValidateSide:
    def test_buy_normalised(self):
        assert validate_side("buy") == "BUY"

    def test_sell_normalised(self):
        assert validate_side("sell") == "SELL"

    def test_mixed_case(self):
        assert validate_side("BuY") == "BUY"

    def test_invalid_side_raises(self):
        with pytest.raises(ValidationError, match="BUY or SELL"):
            validate_side("HOLD")

    def test_empty_side_raises(self):
        with pytest.raises(ValidationError, match="BUY or SELL"):
            validate_side("")


class TestValidateOrderType:
    def test_market(self):
        assert validate_order_type("market") == "MARKET"

    def test_limit(self):
        assert validate_order_type("limit") == "LIMIT"

    def test_stop_market(self):
        assert validate_order_type("stop_market") == "STOP_MARKET"

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError, match="MARKET, LIMIT, or STOP_MARKET"):
            validate_order_type("trailing_stop")


class TestValidateQuantity:
    def test_float_string(self):
        assert validate_quantity("0.5") == 0.5

    def test_integer(self):
        assert validate_quantity(1) == 1.0

    def test_zero_raises(self):
        with pytest.raises(ValidationError, match="positive"):
            validate_quantity(0)

    def test_negative_raises(self):
        with pytest.raises(ValidationError, match="positive"):
            validate_quantity(-0.1)

    def test_non_numeric_string_raises(self):
        with pytest.raises(ValidationError, match="number"):
            validate_quantity("abc")


class TestValidatePrice:
    def test_none_for_market_is_ok(self):
        assert validate_price(None, "MARKET") is None

    def test_none_for_limit_raises(self):
        with pytest.raises(ValidationError, match="required for LIMIT"):
            validate_price(None, "LIMIT")

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError, match="positive"):
            validate_price(-100, "LIMIT")

    def test_valid_price(self):
        assert validate_price("3200.50", "LIMIT") == 3200.50

    def test_non_numeric_price_raises(self):
        with pytest.raises(ValidationError, match="number"):
            validate_price("free", "LIMIT")


class TestValidateStopPrice:
    def test_none_for_stop_market_raises(self):
        with pytest.raises(ValidationError, match="required for STOP_MARKET"):
            validate_stop_price(None, "STOP_MARKET")

    def test_stop_price_none_for_non_conditional_is_ok(self):
        assert validate_stop_price(None, "MARKET") is None

    def test_negative_stop_price_raises(self):
        with pytest.raises(ValidationError, match="positive"):
            validate_stop_price(-50000, "STOP_MARKET")

    def test_valid_stop_price(self):
        assert validate_stop_price("58000", "STOP_MARKET") == 58000.0


class TestNonFiniteInputs:
    """NaN and infinity used to slip past validation (nan <= 0 is False)."""

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), "nan", "inf", "1e400"])
    def test_quantity_rejects_non_finite(self, bad):
        with pytest.raises(ValidationError, match="finite|positive"):
            validate_quantity(bad)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), "nan"])
    def test_price_rejects_non_finite(self, bad):
        with pytest.raises(ValidationError, match="finite|positive"):
            validate_price(bad, "LIMIT")

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), "inf"])
    def test_stop_price_rejects_non_finite(self, bad):
        with pytest.raises(ValidationError, match="finite|positive"):
            validate_stop_price(bad, "STOP_MARKET")


class TestFormatNumber:

    def test_plain_decimals(self):
        from bot.validators import format_number
        assert format_number(0.01) == "0.01"
        assert format_number(0.00001) == "0.00001"
        assert format_number(10.0) == "10"
        assert format_number(3200.0) == "3200"
        assert format_number(0.1) == "0.1"

    def test_never_scientific_notation(self):
        from bot.validators import format_number
        for value in (1e-5, 1e-7, 5e-8, 1234.5678):
            assert "e" not in format_number(value).lower()

    def test_non_finite_raises(self):
        from bot.validators import format_number
        with pytest.raises(ValidationError):
            format_number(float("nan"))
        with pytest.raises(ValidationError):
            format_number(float("inf"))

    def test_string_input_rejected(self):
        from bot.validators import format_number
        with pytest.raises(TypeError):
            format_number("0.01")
