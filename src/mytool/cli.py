"""The command line: license commands here, the tool's own commands in ``commands.py``"""

from __future__ import annotations

import functools
import json
import sys
from typing import Callable, Optional

import typer

from . import __version__, config, ui
from .licensing import EXIT_ERROR, LicenseError, Licensing, SessionEnded

app = typer.Typer(
    name=config.APP_NAME,
    help=f"{config.APP_NAME}: a command-line tool sold with license keys",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

LICENSE_PANEL = "License"

#: Builds the licensing layer. Tests swap this for one with a fake client
licensing_factory: Callable[[], Licensing] = Licensing


def get_licensing() -> Licensing:
    return licensing_factory()


def friendly(fn):
    """Show licensing and setup errors as one clear line and the right exit code"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SessionEnded as err:
            ui.session_ended(str(err), err.code)
            raise typer.Exit(err.exit_code) from None
        except LicenseError as err:
            ui.error(str(err), err.code)
            raise typer.Exit(err.exit_code) from None
        except config.ConfigError as err:
            ui.error(str(err))
            raise typer.Exit(EXIT_ERROR) from None
        except KeyboardInterrupt:
            ui.error("Cancelled")
            raise typer.Exit(130) from None

    return wrapper


def _confirm_move(assume_yes: bool) -> Callable[[str], bool]:
    def confirm(message: str) -> bool:
        ui.info("This license is in use on another computer")
        if assume_yes:
            return True
        return typer.confirm("Move the license to this computer?", default=False)
    return confirm


def _version_callback(value: bool) -> None:
    if value:
        ui.console.print(f"{config.APP_NAME} {__version__}")
        raise typer.Exit()


@app.callback()
def _root(version: Optional[bool] = typer.Option(None, "--version", callback=_version_callback,
                                                 is_eager=True, help="Show the version and exit")) -> None:
    """License keys, a free trial and a live kill switch, powered by PWF Auth"""


@app.command(rich_help_panel=LICENSE_PANEL)
@friendly
def activate(key: Optional[str] = typer.Argument(None, help="Your license key. Asked for when left out"),
             yes: bool = typer.Option(False, "--yes", "-y", help="Move the license from another computer without asking")) -> None:
    """Activate a license key on this computer"""
    lic = get_licensing()
    if not key:
        key = typer.prompt("License key").strip()
    res = lic.activate(key, confirm_move=_confirm_move(yes))
    ui.ok("License activated on this computer")
    ui.console.print(ui.card_from_login(res, key.strip()))
    if lic.key_from_env:
        ui.info(f"The key came from {config.ENV_LICENSE_KEY}, so it was not saved")


@app.command(rich_help_panel=LICENSE_PANEL)
@friendly
def trial(yes: bool = typer.Option(False, "--yes", "-y", help="Move the trial from another computer without asking")) -> None:
    """Start the free trial on this computer"""
    lic = get_licensing()
    res = lic.trial(confirm_move=_confirm_move(yes))
    key = res.license.license_key if res.license and res.license.license_key else lic.saved_key() or ""
    ui.ok("Free trial started")
    ui.console.print(ui.card_from_login(res, key, title="Free trial"))


@app.command(rich_help_panel=LICENSE_PANEL)
@friendly
def status(as_json: bool = typer.Option(False, "--json", help="Print the license as JSON, for scripts")) -> None:
    """Show this computer's license. Uses no device seat"""
    lic = get_licensing()
    key = lic.require_key()
    res = lic.status()
    if not res.success:
        raise LicenseError(res.message or "The license server does not know this key", res.error_code)
    valid = res.data.get("valid") is True
    if as_json:
        k = res.data.get("key") if isinstance(res.data.get("key"), dict) else {}
        print(json.dumps({"valid": valid, "key": ui.mask_key(key), "status": k.get("status"),
                          "key_type": k.get("key_type"), "duration": k.get("duration"),
                          "expires_at": k.get("expires_at"), "days_remaining": k.get("days_remaining"),
                          "features": res.features}, indent=2))
    else:
        ui.console.print(ui.card_from_check(res, key))
    if not valid:
        raise typer.Exit(2)


@app.command(rich_help_panel=LICENSE_PANEL)
@friendly
def deactivate(yes: bool = typer.Option(False, "--yes", "-y", help="Do not ask first")) -> None:
    """Remove the license key from this computer"""
    lic = get_licensing()
    if not lic.store.get():
        ui.info("No license key is saved on this computer")
        return
    if not yes and not typer.confirm("Remove the license key from this computer?", default=False):
        raise typer.Exit(1)
    lic.forget()
    ui.ok("The license key was removed from this computer")
    ui.info(f"To use it on another computer, run `{config.APP_NAME} activate` there: it offers to move the license")


@app.command(rich_help_panel=LICENSE_PANEL)
@friendly
def update(channel: str = typer.Option("stable", help="stable, beta or alpha")) -> None:
    """Check for a newer version"""
    lic = get_licensing()
    res = lic.check_update(__version__, channel)
    if not res.success:
        raise LicenseError(res.message or "The update check failed", res.error_code)
    if res.data.get("update_available") is not True:
        ui.ok(f"You have the latest version ({__version__})")
        return
    up = res.data.get("update") if isinstance(res.data.get("update"), dict) else {}
    lines = [f"[bold]{config.APP_NAME} {up.get('version', '?')}[/] is out (you have {__version__})"]
    if up.get("is_mandatory"):
        lines.append("[yellow]This update is required.[/]")
    if up.get("changelog"):
        lines.append("")
        lines.append(str(up["changelog"]).strip())
    if up.get("download_url"):
        lines.append("")
        lines.append(f"Download: {lic.absolute_url(up['download_url'])}")
    ui.notice("\n".join(lines), title="Update available")


def _console_safe() -> None:
    """A Windows pipe in a legacy code page cannot print ✓ or •; replace instead of crashing"""
    for stream in (sys.stdout, sys.stderr):
        enc = getattr(stream, "encoding", None) or "utf-8"
        try:
            "✓•●›✗".encode(enc)
        except (UnicodeEncodeError, LookupError):
            try:
                stream.reconfigure(errors="replace")
            except (AttributeError, ValueError):
                pass


def main() -> None:
    _console_safe()
    app()


from . import commands  # noqa: E402,F401  (registers the tool's own commands on `app`)
