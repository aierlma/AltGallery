"""Check that an app-specific generator failure still permits other updates and merge."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UpdateTests(unittest.TestCase):
    def test_custom_generator_failure_continues_and_merges_last_good_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(ROOT / "update.sh", root / "update.sh")
            for name in ("PiliPlus-BTR", "ZGood"):
                app = root / "apps" / name
                app.mkdir(parents=True)
                (app / "config.toml").touch()
                (app / "apps.json").write_text("last good source")
            (root / "apps/PiliPlus-BTR/generate.py").touch()
            binary = root / "bin"
            binary.mkdir()
            (binary / "uv").write_text('#!/bin/sh\nprintf "custom:%s\\n" "$*" >> "$CALL_LOG"\nexit 2\n')
            (binary / "uvx").write_text('#!/bin/sh\nprintf "altgen:%s\\n" "$*" >> "$CALL_LOG"\nexit 0\n')
            for path in binary.iterdir():
                path.chmod(0o755)
            log = root / "calls"
            env = dict(os.environ, PATH=f"{binary}:{os.environ['PATH']}", CALL_LOG=str(log))
            result = subprocess.run(["bash", str(root / "update.sh")], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("apps/PiliPlus-BTR", result.stderr)
            calls = log.read_text().splitlines()
            self.assertEqual(calls[0], "custom:run --no-project --script generate.py")
            self.assertEqual(calls[1], "altgen:altgen -c config.toml")
            self.assertIn("merge -c assets/merge.toml apps/PiliPlus-BTR/apps.json apps/ZGood/apps.json", calls[2].replace("//", "/"))
            self.assertEqual((root / "apps/PiliPlus-BTR/apps.json").read_text(), "last good source")


if __name__ == "__main__":
    unittest.main()
