import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOL = Path(__file__).resolve().parents[1] / "tools/rescue_audit.py"
spec = importlib.util.spec_from_file_location("audit", TOOL)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_binary_reads_without_posix_open_constants(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"binary"
            content = b"line\r\n\x1a\x00\xff"
            p.write_bytes(content)
            with mock.patch.dict(os.__dict__, clear=False):
                for name in ("O_NOFOLLOW", "O_NONBLOCK"):
                    os.__dict__.pop(name, None)
                digest, info = audit.hash_file(p)
            self.assertEqual(digest, audit.hashlib.sha256(content).hexdigest())
            self.assertEqual(info.st_size, len(content))

    def test_reparse_point_rejected_before_open(self):
        fake = mock.Mock(st_mode=audit.stat.S_IFREG, st_file_attributes=0x400)
        with mock.patch.object(audit.os, "lstat", return_value=fake), \
             mock.patch.object(audit.os, "open") as opener:
            with self.assertRaises(ValueError): audit.open_regular("junction")
            opener.assert_not_called()

    def test_missing_extra_and_same_size_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a", Path(tmp)/"b"
            a.mkdir(); b.mkdir()
            for root in (a, b):
                (root/"same").write_bytes(b"abc")
                (root/"empty").mkdir()
            def records(root):
                data = audit.inventory(root)
                self.assertTrue(data["complete"])
                return {r["path"]: r for r in data["records"]}
            self.assertTrue(audit.compare(records(a), records(b))["match"])
            (b/"same").write_bytes(b"abd")
            (b/"extra").touch()
            (b/"empty").rmdir()
            result = audit.compare(records(a), records(b))
            self.assertEqual({r["reason"] for r in result["differences"]}, {"changed", "extra", "missing"})

    def test_symlink_never_hashed_or_recursed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"source"; root.mkdir()
            try:
                (root/"outside").symlink_to(Path(tmp), target_is_directory=True)
            except OSError as e:
                self.skipTest("symlink creation unavailable: " + str(e))
            result = audit.inventory(root)
            self.assertEqual(len(result["records"]), 1)
            self.assertEqual(result["records"][0]["kind"], "symlink")
            with self.assertRaises((OSError, ValueError)):
                audit.hash_file(root/"outside")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO is unavailable")
    def test_special_file_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkfifo(Path(tmp)/"pipe")
            result = audit.inventory(tmp)
            self.assertFalse(result["complete"])
            self.assertEqual(len(result["errors"]), 1)

    def test_manifest_rejects_incomplete_duplicate_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"manifest.json"
            cases = [
                {"schema": audit.SCHEMA, "complete": False, "records": []},
                {"schema": audit.SCHEMA, "complete": True, "records": [{"path": "../escape", "kind": "directory"}]},
                {"schema": audit.SCHEMA, "complete": True, "records": [{"path": "x", "kind": "directory"}]*2},
            ]
            for case in cases:
                p.write_text(json.dumps(case))
                with self.assertRaises(ValueError): audit.load_manifest(p)

    def test_footer_checks_marker_size_and_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"sample.L0CK3D"
            tail = bytearray(588)
            tail[568:572] = bytes.fromhex("11223344")
            tail[572:576] = bytes([0x26, 0, 0x20, 0])
            struct.pack_into("<Q", tail, 580, 3)
            p.write_bytes(b"abc" + tail)
            self.assertTrue(audit.footer(p, "11223344")["layout_match"])
            self.assertFalse(audit.footer(p, "00000000")["layout_match"])
            p.write_bytes(b"abc" + tail + b"trailing")
            self.assertFalse(audit.footer(p, "11223344")["layout_match"])
            tail[574] = 0x21
            p.write_bytes(b"abc" + tail)
            self.assertFalse(audit.footer(p, "11223344")["layout_match"])

    def test_case_unicode_plain_cipher_and_parent_conflicts(self):
        paths = ["A.jpg.L0CK3D", "a.jpg", "é.jpg", "e\u0301.jpg", "node.L0CK3D", "node/child"]
        result = audit.plan({p: {"kind": "file"} for p in paths})
        self.assertEqual(len({r["object_path"] for r in result["outputs"]}), len(paths))
        self.assertEqual(len(result["conflicts"]), 3)
        self.assertIn("file_directory", {r["kind"] for r in result["conflicts"]})

    def test_cli_exclusive_output_and_source_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"source"; root.mkdir()
            (root/"input").write_bytes(b"original")
            output = Path(tmp)/"result.json"
            cmd = [sys.executable, str(TOOL), "--output", str(output), "inventory", str(root)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            saved = output.read_bytes()
            if os.name != "nt":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), saved)
            cmd[3] = str(root/"bad-output.json")
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            self.assertFalse((root/"bad-output.json").exists())
            self.assertEqual((root/"input").read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
