"""Build a single-file executable of the tool with PyInstaller

    PWFAUTH_SECRET=<your app secret> python scripts/build.py

The secret is written into src/mytool/_build_secret.py for the build only and the file
is deleted afterwards, so it never ends up in git. The result is dist/mytool (.exe on
Windows). Needs `pip install -e .[build]`
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "mytool"
SECRET_FILE = PACKAGE / "_build_secret.py"
NAME = "mytool"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--secret-file", help="read the app secret from this file instead of PWFAUTH_SECRET")
    ap.add_argument("--no-secret", action="store_true",
                    help="build without an embedded secret (users then set PWFAUTH_SECRET)")
    args = ap.parse_args()

    secret = ""
    if args.secret_file:
        secret = Path(args.secret_file).read_text(encoding="utf-8").strip()
    elif not args.no_secret:
        secret = os.environ.get("PWFAUTH_SECRET", "").strip()
    if not args.no_secret and not re.fullmatch(r"[0-9a-fA-F]{64}", secret):
        print("Set PWFAUTH_SECRET to the 64-character app secret from the PWF Auth panel "
              "(or pass --secret-file, or --no-secret)", file=sys.stderr)
        return 2

    if secret:
        SECRET_FILE.write_text(
            "# Written by scripts/build.py for one build and deleted afterwards. Never commit it.\n"
            f'APP_SECRET = "{secret.lower()}"\n', encoding="utf-8")
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--clean", "--noconfirm",
               "--name", NAME, "--paths", str(ROOT / "src"),
               "--collect-submodules", "keyring.backends",
               "--copy-metadata", "keyring",
               "--hidden-import", "mytool._build_secret",
               "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
               "--specpath", str(ROOT / "build"),
               str(PACKAGE / "__main__.py")]
        return subprocess.call(cmd, cwd=ROOT)
    finally:
        SECRET_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
