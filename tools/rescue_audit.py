#!/usr/bin/env python3
"""Offline audit helpers. No network, decryption, device access or source writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import sys
import unicodedata

SCHEMA = "c3rb3r-audit-v1"
FOOTER_SIZE = 588


def safe_rel(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise ValueError("unsafe relative path")
    return value


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def is_link(s):
    # Windows junctions and other reparse points must not be traversed either.
    return stat.S_ISLNK(s.st_mode) or bool(getattr(s, "st_file_attributes", 0) & 0x400)


def open_regular(path):
    before = os.lstat(path)
    if is_link(before) or not stat.S_ISREG(before.st_mode):
        raise ValueError("expected a regular file, not a link/device/reparse point")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or identity(before) != identity(s):
        os.close(fd)
        raise ValueError("expected a regular file, not a link/device")
    return os.fdopen(fd, "rb"), s


def hash_file(path):
    f, before = open_regular(path)
    digest = hashlib.sha256()
    with f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
        if identity(before) != identity(os.fstat(f.fileno())):
            raise ValueError("file changed while reading")
    if identity(before) != identity(os.lstat(path)):
        raise ValueError("file replaced while reading")
    return digest.hexdigest(), before


def inventory(root):
    """Inventory stable offline trees; record links without following them."""
    root = Path(root)
    if is_link(root.lstat()):
        raise ValueError("inventory root cannot be a link/reparse point")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be a directory")
    records, errors = [], []
    root_device = root.stat().st_dev

    def walk(directory):
        before = directory.stat()
        try:
            entries = sorted(directory.iterdir(), key=lambda x: x.name)
            for p in entries:
                rel = p.relative_to(root).as_posix()
                try:
                    safe_rel(rel)
                    s = p.lstat()
                    r = {"path": rel}
                    if is_link(s):
                        if not stat.S_ISLNK(s.st_mode):
                            raise ValueError("reparse point/junction is outside this tool's scope")
                        r.update(kind="symlink", target=os.readlink(p))
                    elif stat.S_ISDIR(s.st_mode):
                        if s.st_dev != root_device:
                            raise ValueError("mount boundary: use a separate inventory")
                        r.update(kind="directory")
                    elif stat.S_ISREG(s.st_mode):
                        digest, s = hash_file(p)
                        r.update(kind="file", size=s.st_size, sha256=digest,
                                 nlink=s.st_nlink, mtime_ns=s.st_mtime_ns)
                    else:
                        raise ValueError("special file is outside this tool's scope")
                    records.append(r)
                    if r["kind"] == "directory":
                        walk(p)
                except (OSError, ValueError) as e:
                    errors.append({"path": rel, "error": str(e)})
            if identity(before) != identity(directory.stat()):
                errors.append({"path": str(directory.relative_to(root)),
                               "error": "directory changed while listing"})
        except OSError as e:
            errors.append({"path": str(directory.relative_to(root)), "error": str(e)})

    walk(root)
    return {"schema": SCHEMA, "complete": not errors, "records": records,
            "errors": errors, "limitations": "No ACL/xattr, hardlink topology, Btrfs subvolume or historical-original proof."}


def load_manifest(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ValueError("expected a manifest object with a records list")
    if data.get("schema") != SCHEMA or data.get("complete") is not True or data.get("errors"):
        raise ValueError("manifest is incomplete or unsupported")
    records = {}
    for r in data["records"]:
        if not isinstance(r, dict):
            raise ValueError("expected a record object")
        rel = safe_rel(r["path"])
        if rel in records:
            raise ValueError("duplicate manifest path")
        if r["kind"] not in {"file", "directory", "symlink"}:
            raise ValueError("invalid manifest kind")
        if r["kind"] == "file":
            if not isinstance(r.get("size"), int) or r["size"] < 0:
                raise ValueError("invalid file size")
            digest = r.get("sha256", "")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("invalid SHA-256")
        if r["kind"] == "symlink" and not isinstance(r.get("target"), str):
            raise ValueError("invalid symlink target")
        records[rel] = r
    return records


def compare(left, right):
    differences = []
    for path in sorted(left.keys() | right.keys()):
        a, b = left.get(path), right.get(path)
        if a is None or b is None:
            differences.append({"path": path, "reason": "extra" if a is None else "missing"})
            continue
        fields = ["kind"]
        if a["kind"] == "file":
            fields += ["size", "sha256"]
        if a["kind"] == "symlink":
            fields += ["target"]
        changed = [f for f in fields if a.get(f) != b.get(f)]
        if changed:
            differences.append({"path": path, "reason": "changed", "fields": changed})
    return {"match": not differences, "differences": differences,
            "meaning": "Exact relative paths/types/content; not historical-original or metadata proof."}


def footer(path, marker):
    expected = bytes.fromhex(marker)
    if len(expected) != 4:
        raise ValueError("marker must be exactly four bytes")
    f, before = open_regular(path)
    with f:
        if before.st_size < FOOTER_SIZE:
            raise ValueError("too short for a 588-byte EOF footer")
        f.seek(-FOOTER_SIZE, os.SEEK_END)
        tail = f.read(FOOTER_SIZE)
        if identity(before) != identity(os.fstat(f.fileno())):
            raise ValueError("input changed")
    if identity(before) != identity(os.lstat(path)):
        raise ValueError("input replaced")
    if len(tail) != FOOTER_SIZE:
        raise ValueError("short footer read")
    mode, percent, crypto, reserved = tail[572:576]
    size = struct.unpack_from("<Q", tail, 580)[0]
    checks = {"marker": tail[568:572] == expected,
              "length": size == before.st_size - FOOTER_SIZE,
              "crypto_mode": crypto == 0x20, "reserved": reserved == 0,
              "file_mode": ((mode in (0x24, 0x26) and percent == 0) or
                            (mode == 0x25 and percent in {10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80}))}
    return {"layout_match": all(checks.values()), "checks": checks,
            "observed_marker": tail[568:572].hex(), "mode": hex(mode),
            "partial_parameter": percent, "crypto_mode": hex(crypto),
            "stored_original_size": size,
            "meaning": "Layout only. No key record check, decryption or content authentication."}


def plan(records):
    """Propose flat object names; never create recovered files or resolve conflicts."""
    intended, outputs = {}, []
    for rel, r in sorted(records.items()):
        if r["kind"] != "file":
            continue
        target = rel[:-7] if rel.endswith(".L0CK3D") else rel
        safe_rel(target)
        key = unicodedata.normalize("NFD", target).casefold()
        intended.setdefault(key, []).append(rel)
        outputs.append({"input": rel, "intended_path": target,
                        "object_path": "objects/" + hashlib.sha256(rel.encode("utf-8")).hexdigest(),
                        "action": "decrypt_copy" if rel.endswith(".L0CK3D") else "copy"})
    conflicts = []
    for key, paths in intended.items():
        if len(paths) > 1:
            conflicts.append({"kind": "same_name_case_or_unicode", "inputs": paths})
        parent = PurePosixPath(key).parent
        while str(parent) != ".":
            if str(parent) in intended:
                conflicts.append({"kind": "file_directory", "inputs": intended[str(parent)] + paths})
            parent = parent.parent
    return {"schema": "c3rb3r-path-plan-v1", "outputs": outputs, "conflicts": conflicts,
            "meaning": "Plan only; object names preserve versions. No restore or metadata reconstruction."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("inventory"); p.add_argument("root")
    p = subs.add_parser("compare"); p.add_argument("source_manifest"); p.add_argument("copy_manifest")
    p = subs.add_parser("footer"); p.add_argument("copy"); p.add_argument("--marker", required=True)
    p = subs.add_parser("plan"); p.add_argument("manifest")
    parser.add_argument("--output", required=True, help="New private JSON file outside source trees")
    args = parser.parse_args()
    out = Path(args.output)
    try:
        if args.command == "inventory":
            root = Path(args.root)
            if out.resolve().is_relative_to(root.resolve(strict=True)):
                raise ValueError("output must be outside the inventory root")
            result = inventory(root); ok = result["complete"]
        elif args.command == "compare":
            result = compare(load_manifest(args.source_manifest), load_manifest(args.copy_manifest))
            ok = result["match"]
        elif args.command == "footer":
            result = footer(args.copy, args.marker); ok = result["layout_match"]
        else:
            result = plan(load_manifest(args.manifest)); ok = not result["conflicts"]
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=True, indent=2)
            f.write("\n")
        print(json.dumps({"ok": ok, "output_created": True}))
        return 0 if ok else 1
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
