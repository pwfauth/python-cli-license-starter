"""Where the license key is kept between runs.

The default is the operating system's credential store through ``keyring``: Windows
Credential Manager, the macOS Keychain, or the Secret Service on Linux. Machines with
no credential store (a headless server, a container) fall back to a file readable only
by the current user. ``MYTOOL_STORE=file`` picks the file on purpose.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Protocol

from . import config

_KEYRING_USER = "license-key"
_FILE_NAME = "license.key"


class KeyStore(Protocol):
    """The three things the licensing layer needs from a store."""

    def get(self) -> Optional[str]: ...
    def set(self, key: str) -> None: ...
    def clear(self) -> None: ...


class FileStore:
    """A plain file in the settings folder, mode 0600 where the OS supports it."""

    def __init__(self, folder: Optional[Path] = None) -> None:
        self.path = (folder or config.home_dir()) / _FILE_NAME

    def get(self) -> Optional[str]:
        try:
            return self.path.read_text(encoding="utf-8").strip() or None
        except FileNotFoundError:
            return None

    def set(self, key: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(key)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class KeyringStore:
    """The OS credential store."""

    def __init__(self, service: str = config.APP_NAME) -> None:
        self.service = service

    def get(self) -> Optional[str]:
        import keyring
        return keyring.get_password(self.service, _KEYRING_USER) or None

    def set(self, key: str) -> None:
        import keyring
        keyring.set_password(self.service, _KEYRING_USER, key)

    def clear(self) -> None:
        import keyring
        from keyring.errors import PasswordDeleteError
        try:
            keyring.delete_password(self.service, _KEYRING_USER)
        except PasswordDeleteError:
            pass


def _keyring_usable() -> bool:
    try:
        import keyring
        from keyring.backends import fail
    except Exception:
        return False
    try:
        return not isinstance(keyring.get_keyring(), fail.Keyring)
    except Exception:
        return False


def default_store() -> KeyStore:
    """The store this machine should use (see the module docstring)."""
    wanted = os.environ.get(config.ENV_STORE, "").strip().lower()
    if wanted == "file" or (wanted != "keyring" and not _keyring_usable()):
        return FileStore()
    return KeyringStore()
