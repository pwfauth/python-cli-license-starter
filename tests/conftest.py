"""A fake license server client, so the tests run offline and in a second."""

from __future__ import annotations

import threading
from typing import Optional

import pytest
from typer.testing import CliRunner

from pwfauth import PwfHttpError, PwfResponse

from mytool import cli
from mytool.licensing import Licensing

GOOD = "GOOD-1111-2222-3333"
TURBO = "TURB-1111-2222-3333"
ELSEWHERE = "MOVE-1111-2222-3333"


def reply(**data) -> PwfResponse:
    return PwfResponse(data=data, is_enveloped=True, status_code=200)


def user(key: str, **extra) -> dict:
    u = {"license_key": key, "key_type": "days", "duration": 30, "hwid": "h", "status": "active",
         "activated_at": "2026-10-01T10:00:00Z", "expires_at": "2026-10-31T10:00:00Z", "days_remaining": 8}
    u.update(extra)
    return u


class MemoryStore:
    def __init__(self, key: Optional[str] = None) -> None:
        self.key = key

    def get(self):
        return self.key

    def set(self, key):
        self.key = key

    def clear(self):
        self.key = None


class FakeClient:
    """The PwfClient methods the tool uses, answering like the real server."""

    base_url = "https://pwfauth.com"

    def __init__(self) -> None:
        self.calls: list = []
        self.bound_elsewhere = {ELSEWHERE}
        self.vars: dict = {}
        self.on_session_ended = None
        self.end_after: Optional[float] = None    # seconds after start_heartbeat to "ban" the key
        self.offline = False
        self.trial_reply = reply(success=True, trial_key=GOOD)
        self.session = None

    def _log(self, name, *args):
        self.calls.append((name,) + args)
        if self.offline:
            raise PwfHttpError("no reply", 0)

    def login(self, key):
        self._log("login", key)
        if key in self.bound_elsewhere:
            return reply(success=False, error_code="HWID_MISMATCH",
                         message="This license is bound to another computer.")
        if key not in (GOOD, TURBO, ELSEWHERE):
            return reply(success=False, error_code="INVALID_KEY", message="Invalid license key.")
        self.session = "s-1"
        return reply(success=True, session_id="s-1", user=user(key), features={"turbo": key == TURBO},
                     texts={"motd": "Version 2 is coming in November."}, app={"message": ""})

    def logout(self):
        self._log("logout")
        self.session = None

    def check_key(self, key):
        self._log("check_key", key)
        if key not in (GOOD, TURBO):
            return reply(success=False, valid=False, error_code="INVALID_KEY", message="Key not found.")
        return reply(success=True, valid=True, key={"status": "active", "key_type": "days", "duration": 30,
                                                    "expires_at": "2026-10-31T10:00:00Z", "days_remaining": 8},
                     features={"turbo": key == TURBO})

    def reset_hardware_id(self, key, reason=None):
        self._log("reset_hardware_id", key)
        self.bound_elsewhere.discard(key)   # the next login binds it to this computer
        return reply(success=True)

    def create_trial(self):
        self._log("create_trial")
        return self.trial_reply

    def check_update(self, version, channel="stable"):
        self._log("check_update", version, channel)
        return reply(success=True, update_available=True,
                     update={"version": "1.1.0", "changelog": "- Faster runs", "is_mandatory": False,
                             "download_url": "api/update/download.php?v=1.1.0"})

    def start_heartbeat(self):
        self._log("start_heartbeat")
        if self.end_after is not None:
            def ban():
                cb = self.on_session_ended
                self.session = None
                if cb:
                    cb("BANNED", "This license has been banned.")
            threading.Timer(self.end_after, ban).start()

    def get_variable(self, name):
        return self.vars.get(name)

    def set_variable(self, name, value):
        self.vars[name] = value


@pytest.fixture
def fake(monkeypatch):
    """(client, store); the CLI builds its Licensing from these."""
    client, store = FakeClient(), MemoryStore()
    monkeypatch.setattr(cli, "licensing_factory",
                        lambda: Licensing(client=client, store=store, grace_seconds=30))
    monkeypatch.delenv("MYTOOL_LICENSE_KEY", raising=False)
    return client, store


@pytest.fixture
def runner():
    return CliRunner()
