"""Terminal output: the license card, notices and errors"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(highlight=False)
err_console = Console(stderr=True, highlight=False)

ACCENT = "cyan"
_STATUS_STYLE = {
    "active": ("Active", "green"),
    "unused": ("Not activated yet", "yellow"),
    "expired": ("Expired", "red"),
    "banned": ("Banned", "red"),
    "paused": ("Paused", "yellow"),
}


def mask_key(key: Optional[str]) -> str:
    """``ABCD-1234-EF56-7890`` → ``ABCD-••••-••••-7890``: enough to recognise, not to reuse"""
    if not key:
        return "-"
    parts = key.split("-")
    if len(parts) >= 3:
        return "-".join([parts[0]] + ["••••"] * (len(parts) - 2) + [parts[-1]])
    return key[:4] + "••••" + key[-4:] if len(key) > 10 else "••••"


def _plan(key_type: Optional[str], duration) -> str:
    if not key_type:
        return "-"
    if key_type == "lifetime":
        return "Lifetime"
    if isinstance(duration, int) or (isinstance(duration, str) and duration.isdigit()):
        n = int(duration)
        unit = key_type.rstrip("s")
        return f"{n} {unit}{'' if n == 1 else 's'}"
    return key_type.capitalize()


def _parse(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace(" ", "T").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _expiry(expires, days_left, key_type: Optional[str]) -> Text:
    if key_type == "lifetime":
        return Text("Never", style="green")
    dt = _parse(expires)
    if dt is None:
        return Text("Starts on first activation", style="dim")
    when = dt.astimezone().strftime("%d %b %Y, %H:%M")
    out = Text(when)
    if isinstance(days_left, int):
        style = "red" if days_left <= 3 else ("yellow" if days_left <= 7 else "dim")
        out.append(f"  ({days_left} day{'' if days_left == 1 else 's'} left)", style=style)
    return out


def license_card(*, key: Optional[str], status: Optional[str], key_type: Optional[str], duration,
                 expires, days_left, features: Optional[dict] = None, title: str = "License") -> Panel:
    label, style = _STATUS_STYLE.get((status or "").lower(), ((status or "Unknown").capitalize(), "yellow"))
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    grid.add_row("Status", Text("● " + label, style=style))
    grid.add_row("Key", mask_key(key))
    grid.add_row("Plan", _plan(key_type, duration))
    grid.add_row("Expires", _expiry(expires, days_left, key_type))
    on = [name for name, v in (features or {}).items() if v in (True, 1, "1", "true", "on", "yes")]
    if on:
        grid.add_row("Features", ", ".join(sorted(on)))
    return Panel(grid, title=f"[bold]{title}[/]", title_align="left", border_style=ACCENT,
                 padding=(1, 2), expand=False)


def card_from_login(res, key: str, title: str = "License") -> Panel:
    lic = res.license
    return license_card(key=key, status=lic.status if lic else "active", key_type=lic.key_type if lic else None,
                        duration=lic.duration if lic else None, expires=lic.expires_at if lic else None,
                        days_left=lic.days_remaining if lic else None, features=res.features, title=title)


def card_from_check(res, key: str) -> Panel:
    k = res.data.get("key") if isinstance(res.data.get("key"), dict) else {}
    return license_card(key=key, status=k.get("status"), key_type=k.get("key_type"), duration=k.get("duration"),
                        expires=k.get("expires_at"), days_left=k.get("days_remaining"), features=res.features)


def tidy(message: str) -> str:
    """One line for the terminal: server messages arrive with a final period, ours have none"""
    message = (message or "").strip()
    return message[:-1] if message.endswith(".") and not message.endswith("..") else message


def ok(message: str) -> None:
    console.print(f"[green]✓[/] {tidy(message)}")


def info(message: str) -> None:
    console.print(f"[{ACCENT}]›[/] {tidy(message)}")


def notice(message: str, title: str = "Notice") -> None:
    console.print(Panel(message.strip(), title=title, title_align="left", border_style="yellow",
                        padding=(0, 1), expand=False))


def error(message: str, code: Optional[str] = None) -> None:
    tail = f" [dim]({code})[/]" if code and code.isupper() else ""
    err_console.print(f"[red]✗[/] {tidy(message)}{tail}")


def session_ended(message: str, code: Optional[str]) -> None:
    err_console.print()
    err_console.print(Panel(f"{tidy(message)}\n[dim]The tool stopped because the license is no longer valid "
                            f"on this computer[/]", title=f"[bold red]License ended[/] [dim]{code or ''}[/]",
                            title_align="left", border_style="red", padding=(0, 1), expand=False))
