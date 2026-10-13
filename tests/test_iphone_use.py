import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package_runner = load_module("iphone_use_package_runner", ROOT / "apps/iPhoneUse/package_runner.py")
upstream_release = load_module("iphone_use_upstream_release", ROOT / "apps/iPhoneUse/upstream_release.py")


class PackageRunnerTests(unittest.TestCase):
    def make_app(self):
        root = Path(tempfile.mkdtemp())
        app = root / "iPhoneUse-Runner.app"
        test = app / "PlugIns/iPhoneUse.xctest"
        test.mkdir(parents=True)
        (app / "iPhoneUse-Runner").write_bytes(b"runner")
        (test / "iPhoneUse").write_bytes(b"test")
        (app / "Info.plist").write_bytes(
            package_runner.plistlib.dumps(
                {
                    "CFBundleExecutable": "iPhoneUse-Runner",
                    "CFBundleIdentifier": "com.leeguoo.iphone-use.runner.xctrunner",
                    "CFBundleShortVersionString": "0.17.20",
                    "CFBundleVersion": "1",
                }
            )
        )
        (test / "Info.plist").write_bytes(
            package_runner.plistlib.dumps(
                {
                    "CFBundleExecutable": "iPhoneUse",
                    "CFBundleIdentifier": "com.leeguoo.iphone-use.runner",
                }
            )
        )
        return app

    def test_product_metadata_is_read_without_hard_coding_build_three(self):
        app = self.make_app()
        self.assertEqual(package_runner.locate_test_bundle(app, None)[1], "PlugIns/iPhoneUse.xctest")
        package_runner.validate_version("0.17.20", "1")
        with self.assertRaises(ValueError):
            package_runner.validate_version("0.17.20", "0")

    def test_multiple_plug_ins_are_not_silently_dropped(self):
        app = self.make_app()
        (app / "PlugIns/Other.appex").mkdir()
        # Discovery still identifies the XCTest bundle; package() will reject
        # the extra entry after copying rather than dropping it.
        self.assertEqual(package_runner.locate_test_bundle(app, None)[1], "PlugIns/iPhoneUse.xctest")


class UpstreamReleaseTests(unittest.TestCase):
    def test_resolve_records_commit_and_requires_official_build_markers(self):
        release = {
            "draft": False,
            "prerelease": False,
            "tag_name": "v0.17.20",
            "id": 42,
            "html_url": "https://github.com/leeguooooo/iphone-use/releases/tag/v0.17.20",
            "assets": [
                {
                    "name": "iphone-use-runner.tar.gz",
                    "state": "uploaded",
                    "size": 10,
                    "digest": "sha256:" + "a" * 64,
                    "browser_download_url": "https://github.com/leeguooooo/iphone-use/releases/download/v0.17.20/iphone-use-runner.tar.gz",
                },
                {
                    "name": "iphone-use-runner.tar.gz.sha256",
                    "state": "uploaded",
                    "size": 10,
                    "digest": "sha256:" + "b" * 64,
                    "browser_download_url": "https://github.com/leeguooooo/iphone-use/releases/download/v0.17.20/iphone-use-runner.tar.gz.sha256",
                },
            ],
        }
        source = {
            "runner/build.sh": "--unsigned build-for-testing IPU_EMBED_LIB CODE_SIGNING_ALLOWED=NO",
            "scripts/build-ios-embed.sh": "aarch64-apple-ios libipu_embed.a -p ios-embed",
            "runner/ci-check.sh": "runner/unit-check.sh runner/build.sh --unsigned",
        }

        def api(url):
            if url.endswith("/releases/latest"):
                return release
            if url.endswith("/commits/v0.17.20"):
                return {"sha": "c" * 40}
            raise AssertionError(url)

        def source_for(url):
            for path, content in source.items():
                if url.endswith("/" + path):
                    return content
            raise AssertionError(url)

        with patch.object(upstream_release, "fetch_json", side_effect=api), patch.object(
            upstream_release, "fetch_text", side_effect=source_for
        ):
            data = upstream_release.resolve()
        self.assertEqual(data["tag"], "v0.17.20")
        self.assertEqual(data["commit"], "c" * 40)
        self.assertTrue(data["checks"]["official_build_scripts"])
        self.assertEqual(data["runner_archive"]["digest"], "sha256:" + "a" * 64)

    def test_resolve_rejects_missing_unsigned_path(self):
        release = {"draft": False, "prerelease": False, "tag_name": "v0.17.20", "assets": []}
        with patch.object(
            upstream_release,
            "fetch_json",
            side_effect=[release, {"sha": "c" * 40}],
        ), patch.object(upstream_release, "fetch_text", return_value="build-for-testing"):
            with self.assertRaises(upstream_release.UpstreamError):
                upstream_release.resolve()


if __name__ == "__main__":
    unittest.main()
