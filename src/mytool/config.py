"""Settings: the tool's name, its app secret and where it keeps files.

Everything that changes when you rename the template lives here.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

#: Used for the keyring entry, the settings folder and the environment variables.
APP_NAME = "mytool"

#: Environment variables. ``PWFAUTH_SECRET`` matches the pwfauth package's own docs.
ENV_SECRET = "PWFAUTH_SECRET"
ENV_LICENSE_KEY = "MYTOOL_LICENSE_KEY"   # a key for CI and servers; never saved
ENV_HOME = "MYTOOL_HOME"                 # override the settings folder
ENV_STORE = "MYTOOL_STORE"               # "keyring" (default) or "file"

_SECRET_RE = re.compile(r"[0-9a-fA-F]{64}")


class ConfigError(Exception):
    """The tool is not set up correctly. The message says how to fix it."""


def app_secret() -> str:
    """The app secret from the PWF Auth panel (Applications, then your app).

    Read from ``PWFAUTH_SECRET`` first, then from ``_build_secret.py``, which
    ``scripts/build.py`` writes for a release build and deletes again. Neither is
    ever committed.
    """
    secret = os.environ.get(ENV_SECRET, "").strip()
    if not secret:
        try:
            from ._build_secret import APP_SECRET  # type: ignore[import-not-found]
        except ImportError:
            APP_SECRET = ""
        secret = APP_SECRET.strip()
    if not secret:
        raise ConfigError(
            f"No app secret. Set {ENV_SECRET} to your app's secret from the PWF Auth panel, "
            "or build a release with scripts/build.py.")
    if not _SECRET_RE.fullmatch(secret):
        raise ConfigError(f"{ENV_SECRET} must be the 64-character app secret from the PWF Auth panel.")
    return secret.lower()


def home_dir() -> Path:
    """The tool's settings folder (created on first use)."""
    override = os.environ.get(ENV_HOME, "").strip()
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME
