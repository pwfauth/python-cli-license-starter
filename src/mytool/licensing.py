"""The licensing layer: the only module that talks to the license server

Commands use three things from here:

* :meth:`Licensing.activate` and :meth:`Licensing.trial` put a key on this computer;
* :meth:`Licensing.status` reads it without opening a session;
* :meth:`Licensing.session` wraps the tool's real work. It opens a session, keeps it
  alive with a heartbeat, and stops the work when the license stops being valid
  (a ban, a pause, expiry, a move to another PC, or a server that stopped answering)

It uses the official ``pwfauth`` package (https://pwfauth.com). To use another
license backend, this is the only file to rewrite
"""

from __future__ import annotations

import _thread
import os
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional
from urllib.parse import urljoin

from pwfauth import (PwfClient, PwfCryptoError, PwfError, PwfErrorCodes, PwfHttpError,
                     PwfRefusedError, PwfResponse, PwfSecurityError)

from . import config
from .store import KeyStore, default_store

EXIT_ERROR = 1           # setup or network problem
EXIT_LICENSE = 2         # no license, or the server refused it
EXIT_SESSION_ENDED = 3   # the license stopped being valid while the tool was working

#: How long the work may keep running after the session ended before the process is
#: stopped hard. Plenty for a loop that checks; a call stuck in C code gets stopped
DEFAULT_GRACE_SECONDS = 10.0

_MOVE_CODES = frozenset({PwfErrorCodes.HWID_MISMATCH, PwfErrorCodes.DEVICE_LIMIT})


class LicenseError(Exception):
    """A licensing problem the user can act on. ``str(err)`` is safe to show"""

    def __init__(self, message: str, code: Optional[str] = None, exit_code: int = EXIT_LICENSE) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


class SessionEnded(LicenseError):
    """The license stopped being valid while the tool was working"""

    def __init__(self, code: Optional[str], message: Optional[str]) -> None:
        super().__init__(message or "The license is no longer valid on this computer",
                         code, EXIT_SESSION_ENDED)


def refusal(res: PwfResponse) -> LicenseError:
    """A server refusal as an error with the server's own message"""
    return LicenseError(res.message or res.error_code or "The license server refused the request",
                        res.error_code)


def normalize_key(key: str) -> str:
    return (key or "").strip()


@dataclass
class Session:
    """An open license session, handed to the tool's work"""

    response: PwfResponse
    client: PwfClient
    _ended: dict = field(default_factory=dict, repr=False)

    @property
    def license(self):
        """The license block (type, expiry, days left). See ``pwfauth.License``"""
        return self.response.license

    def text(self, name: str) -> Optional[str]:
        """A remote text (panel: Texts & slides), with this key's override applied"""
        texts = self.response.data.get("texts")
        value = texts.get(name) if isinstance(texts, dict) else None
        return value if isinstance(value, str) and value.strip() else None

    @property
    def login_message(self) -> Optional[str]:
        """The app's sign-in message (panel: Applications, then Login message)"""
        app = self.response.data.get("app")
        msg = app.get("message") if isinstance(app, dict) else None
        return msg if isinstance(msg, str) and msg.strip() else None

    def get_variable(self, name: str) -> Optional[str]:
        """A value stored on the server for this customer (panel: Licences, then Variables)"""
        return self.client.get_variable(name)

    def set_variable(self, name: str, value: str) -> None:
        self.client.set_variable(name, value)

    def bump_counter(self, name: str) -> Optional[int]:
        """Add one to a numeric user variable and return the new value

        Counters are a nice-to-have: None when the server refuses, so a full
        variable store never stops a paid run
        """
        try:
            current = self.client.get_variable(name)
            value = (int(current) if current and current.strip().isdigit() else 0) + 1
            self.client.set_variable(name, str(value))
            return value
        except (PwfRefusedError, PwfError):
            return None

    def ensure_active(self) -> None:
        """Raise :class:`SessionEnded` if the license ended. Call it between work steps"""
        if self._ended:
            raise SessionEnded(*self._ended["reason"])


class Licensing:
    """License keys for this tool on this computer"""

    def __init__(self, *, client: Optional[PwfClient] = None, store: Optional[KeyStore] = None,
                 grace_seconds: float = DEFAULT_GRACE_SECONDS) -> None:
        self._client = client
        self.store = store or default_store()
        self.grace_seconds = grace_seconds

    @property
    def client(self) -> PwfClient:
        if self._client is None:
            self._client = PwfClient(config.app_secret())
        return self._client

    # the saved key

    @property
    def key_from_env(self) -> bool:
        return bool(os.environ.get(config.ENV_LICENSE_KEY, "").strip())

    def saved_key(self) -> Optional[str]:
        """``MYTOOL_LICENSE_KEY`` if set, else the key saved by ``activate``"""
        return normalize_key(os.environ.get(config.ENV_LICENSE_KEY, "")) or self.store.get()

    def require_key(self) -> str:
        key = self.saved_key()
        if not key:
            raise LicenseError(
                f"This computer has no license yet. Run `{config.APP_NAME} activate` with your key, "
                f"or `{config.APP_NAME} trial` for a free trial", "NO_LICENSE")
        return key

    def forget(self) -> Optional[str]:
        """Remove the saved key from this computer. Returns the key that was removed"""
        key = self.store.get()
        self.store.clear()
        return key

    # putting a key on this computer

    def activate(self, key: str, *, confirm_move: Callable[[str], bool]) -> PwfResponse:
        """Bind ``key`` to this computer and save it

        When the key is already bound to another computer, ``confirm_move`` gets the
        server's message; returning True moves the license here (the panel decides
        whether customers may do that, and how often)
        """
        key = normalize_key(key)
        if not key:
            raise LicenseError("Enter a license key", PwfErrorCodes.MISSING_FIELDS)
        res = self._call(self.client.login, key)
        if not res.success and res.error_code in _MOVE_CODES:
            if not confirm_move(res.message or "This key is used on another computer"):
                raise refusal(res)
            moved = self._call(self.client.reset_hardware_id, key, f"{config.APP_NAME} activate")
            if not moved.success:
                raise refusal(moved)
            res = self._call(self.client.login, key)
        if not res.success:
            raise refusal(res)
        self.client.logout()   # activation only binds the key; each run opens its own session
        if not self.key_from_env:
            self.store.set(key)
        return res

    def trial(self, *, confirm_move: Callable[[str], bool]) -> PwfResponse:
        """Ask for this computer's free trial key and activate it"""
        res = self._call(self.client.create_trial)
        key = res.data.get("trial_key")
        if not isinstance(key, str) or not key:
            raise refusal(res)
        return self.activate(key, confirm_move=confirm_move)

    # reading the license

    def status(self) -> PwfResponse:
        """The saved key's state, without opening a session or using a device seat"""
        return self._call(self.client.check_key, self.require_key())

    def check_update(self, current_version: str, channel: str = "stable") -> PwfResponse:
        return self._call(self.client.check_update, current_version, channel)

    def absolute_url(self, path: str) -> str:
        return urljoin(self.client.base_url + "/", path or "")

    # a licensed run

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Open a session for the duration of the ``with`` block

        The heartbeat runs in the background. When the license ends mid-run, the
        main thread gets a ``KeyboardInterrupt`` that this turns into
        :class:`SessionEnded`; work that cannot be interrupted is stopped after
        ``grace_seconds``. Work loops can also call :meth:`Session.ensure_active`
        """
        key = self.require_key()
        client = self.client
        res = self._call(client.login, key)
        if not res.success:
            raise refusal(res)

        state: dict = {}
        lock = threading.Lock()
        active = [True]
        timer: list = []

        def on_session_ended(code: Optional[str], message: Optional[str]) -> None:
            with lock:
                if not active[0] or state:
                    return
                state["reason"] = (code, message)
                hard_stop = threading.Timer(self.grace_seconds, _hard_exit, args=(code, message))
                hard_stop.daemon = True
                hard_stop.start()
                timer.append(hard_stop)
            _thread.interrupt_main()

        client.on_session_ended = on_session_ended
        session = Session(res, client, state)
        client.start_heartbeat()
        try:
            yield session
            session.ensure_active()
        except KeyboardInterrupt:
            if state:
                raise SessionEnded(*state["reason"]) from None
            raise
        finally:
            with lock:
                active[0] = False
                for t in timer:
                    t.cancel()
            client.on_session_ended = None
            if not state:
                client.logout()

    # helpers

    @staticmethod
    def _call(fn, *args):
        """Run one SDK call, turning transport and security errors into plain sentences"""
        try:
            return fn(*args)
        except PwfSecurityError:
            raise LicenseError("The reply did not come from the license server, so the tool stays locked",
                               "SECURITY", EXIT_ERROR) from None
        except PwfCryptoError:
            raise LicenseError("The license server could not read this request. "
                               f"Check {config.ENV_SECRET}: it must be this app's secret",
                               PwfErrorCodes.CRYPTO_ERROR, EXIT_ERROR) from None
        except PwfHttpError as err:
            if err.status == 0:
                msg = "Cannot reach the license server. Check the internet connection and try again"
            elif err.status == 401:
                msg = f"The license server did not accept this app. Check {config.ENV_SECRET}"
            else:
                msg = f"The license server answered with HTTP {err.status}. Try again in a minute"
            raise LicenseError(msg, "HTTP", EXIT_ERROR) from None
        except config.ConfigError as err:
            raise LicenseError(str(err), "CONFIG", EXIT_ERROR) from None


def _hard_exit(code: Optional[str], message: Optional[str]) -> None:
    sys.stderr.write(f"\nLicense ended ({code}): {message or ''}\n")
    sys.stderr.flush()
    os._exit(EXIT_SESSION_ENDED)
