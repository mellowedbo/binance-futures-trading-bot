import logging
import os

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bot.client import BinanceAPIError, BinanceClient, NetworkError, ValidationError
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

load_dotenv()

app = typer.Typer(add_completion=False)
console = Console()
logger = logging.getLogger("bot.cli")


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value or value.startswith("your_"):
        console.print(
            Panel(
                f"[red]{key} is not set.[/red]\n"
                "Create a .env file from .env.example and fill in your Binance "
                "Testnet credentials.",
                title="Missing Configuration",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    return value


def _render_request_panel(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
    stop_price: float | None,
) -> None:
    rows = [
        f"[bold]Symbol[/bold]    : {symbol}",
        f"[bold]Side[/bold]      : {side}",
        f"[bold]Type[/bold]      : {order_type}",
        f"[bold]Quantity[/bold]  : {quantity}",
    ]
    if price is not None:
        rows.append(f"[bold]Price[/bold]     : {price}")
    if stop_price is not None:
        rows.append(f"[bold]Stop Price[/bold]: {stop_price}")
    console.print(Panel("\n".join(rows), title="Order Request", border_style="cyan"))


def _render_response_panel(response: dict) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Order ID", str(response.get("orderId", "n/a")))
    table.add_row("Status", str(response.get("status", "n/a")))
    table.add_row("Executed Qty", str(response.get("executedQty", "n/a")))
    table.add_row("Avg Price", str(response.get("avgPrice", "n/a")))
    console.print(
        Panel(table, title="Order Result", border_style="green")
    )
    console.print("[bold green]\u2705 Order placed successfully[/bold green]")


def _handle_validation_error(exc: ValidationError) -> None:
    console.print(
        Panel(f"[red]{exc}[/red]", title="Validation Error", border_style="red")
    )
    raise typer.Exit(code=1)


def _handle_api_error(exc: BinanceAPIError) -> None:
    logger.error("order rejected: [%s] %s", exc.code, exc.msg)
    console.print(
        Panel(
            f"[red]Binance rejected the order: [{exc.code}] {exc.msg}[/red]",
            title="API Error",
            border_style="red",
        )
    )
    raise typer.Exit(code=1)


def _handle_network_error(exc: NetworkError) -> None:
    logger.error("network failure: %s", exc)
    console.print(
        Panel(
            "[red]Could not reach Binance. Check your internet connection and "
            "try again.[/red]",
            title="Network Error",
            border_style="red",
        )
    )
    raise typer.Exit(code=1)


def _validate_inputs(
    symbol: str, side: str, order_type: str, quantity: str,
    price: str | None, stop_price: str | None,
) -> tuple[str, str, str, float, float | None, float | None]:
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)
    clean_stop = validate_stop_price(stop_price, clean_type)
    return clean_symbol, clean_side, clean_type, clean_qty, clean_price, clean_stop


def _dispatch_order(
    manager: OrderManager, order_type: str, symbol: str, side: str,
    quantity: float, price: float | None, stop_price: float | None,
) -> dict:
    if order_type == "MARKET":
        return manager.place_market_order(symbol, side, quantity)
    if order_type == "LIMIT":
        return manager.place_limit_order(symbol, side, quantity, price)
    return manager.place_stop_market_order(symbol, side, quantity, stop_price)


def _execute_order(
    manager: OrderManager, order_type: str, symbol: str, side: str,
    quantity: float, price: float | None, stop_price: float | None,
) -> dict | None:
    try:
        return _dispatch_order(
            manager, order_type, symbol, side, quantity, price, stop_price
        )
    except BinanceAPIError as exc:
        _handle_api_error(exc)
    except NetworkError as exc:
        _handle_network_error(exc)
    return None


@app.command()
def place_order(
    symbol: str = typer.Option(..., help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., help="BUY or SELL"),
    type: str = typer.Option("MARKET", "--type", help="MARKET, LIMIT, or STOP_MARKET"),
    quantity: str = typer.Option(..., help="Order quantity"),
    price: str | None = typer.Option(None, help="Limit price (required for LIMIT)"),
    stop_price: str | None = typer.Option(
        None, help="Stop price (required for STOP_MARKET)"
    ),
) -> None:
    setup_logging()
    try:
        sym, sd, ot, qty, pr, sp = _validate_inputs(
            symbol, side, type, quantity, price, stop_price
        )
    except ValidationError as exc:
        _handle_validation_error(exc)
        return

    api_key = _require_env("BINANCE_TESTNET_API_KEY")
    api_secret = _require_env("BINANCE_TESTNET_API_SECRET")
    _render_request_panel(sym, sd, ot, qty, pr, sp)

    manager = OrderManager(BinanceClient(api_key, api_secret))
    resp = _execute_order(manager, ot, sym, sd, qty, pr, sp)
    if resp is not None:
        _render_response_panel(resp)


if __name__ == "__main__":
    app()
