#!/usr/bin/env python3
"""Check tracked/public source files for broken local links and obvious leaks."""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {".L0CK3D", ".raw", ".bin", ".lime", ".dmp", ".core", ".key", ".pem",
           ".log", ".tar", ".gz", ".zip", ".part", ".partial"}
PATTERNS = [
    ("private home path", r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
    ("private key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ("GitHub token", r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("credential assignment", r'(?i)["\x27]?(?:password|access_token|refresh_token)["\x27]?\s*[:=]\s*["\x27][^"\x27\s]{8,}'),
]


def main():
    git = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if git.returncode == 0 and git.stdout:
        files = [ROOT / p.decode() for p in git.stdout.split(b"\0") if p]
    else:
        files = [p for p in ROOT.rglob("*") if p.is_file() and not any(
            part in {".git", "__pycache__", ".venv"} for part in p.relative_to(ROOT).parts)]
    errors = []
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        if p.is_symlink() or p.suffix in BLOCKED or any(
                part in {"private", "evidence", "receipts", "local-validation"} for part in p.relative_to(ROOT).parts):
            errors.append(f"{rel}: forbidden public artifact")
            continue
        try:
            data = p.read_text(encoding="utf-8")
        except UnicodeError:
            errors.append(f"{rel}: unexpected binary file")
            continue
        for label, pattern in PATTERNS:
            if re.search(pattern, data):
                errors.append(f"{rel}: {label}")
        if p.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", data):
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                target = unquote(target.split("#", 1)[0].strip("<>"))
                if target and not (p.parent / target).is_file():
                    errors.append(f"{rel}: broken local link {target}")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"Checked {len(files)} public files; {len(errors)} issues. Pattern scanning is not a secrecy guarantee.")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
