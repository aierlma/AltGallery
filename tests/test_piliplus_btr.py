"""Offline checks for stable release selection and actual IPA metadata."""

import hashlib
import importlib.util
import io
import plistlib
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from altgen.config import load_config

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "PiliPlus-BTR"
spec = importlib.util.spec_from_file_location("btr_generator", APP / "generate.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
from ipa_bundle_id import IpaError


def ipa(**overrides):
    info = {
        "CFBundlePackageType": "APPL",
        "CFBundleIdentifier": "com.example.piliplus.btr",
        "CFBundleShortVersionString": "2.1.4",
        "CFBundleVersion": "5418",
        "MinimumOSVersion": "15.0",
    }
    info.update(overrides)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Payload/Runner.app/Info.plist", plistlib.dumps(info, fmt=plistlib.FMT_BINARY))
        archive.writestr("Payload/Runner.app/PlugIns/Other.app/Info.plist", plistlib.dumps({"CFBundleIdentifier": "wrong.extension"}))
    return buffer.getvalue()


def release(number=15, *, prerelease=False, name=None, payload=None):
    payload = ipa() if payload is None else payload
    return {
        "tag_name": f"v2.1.4-btr.{number}",
        "published_at": "2026-09-22T11:45:22Z",
        "prerelease": prerelease,
        "assets": [{
            "name": name or f"PiliPlus-BTR-ios-2.1.4-btr.{number}-unsigned.ipa",
            "browser_download_url": f"https://github.com/example/releases/download/btr.{number}/release.ipa",
            "size": len(payload),
            "digest": f"sha256:{hashlib.sha256(payload).hexdigest()}",
        }],
    }


class BtrGenerationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(APP / "config.toml")

    def test_older_version_or_build_cannot_replace_a_newer_source(self):
        previous = {"apps": [{"versions": [{"version": "2.1.5506", "buildVersion": "5506", "downloadURL": "current"}]}]}
        for version, build in (("2.1.5502", "5502"), ("2.0.6000", "6000"), ("2.2.0", "5502")):
            data = {"apps": [{"versions": [{"version": version, "buildVersion": build, "downloadURL": "new"}]}]}
            with self.subTest(version=version, build=build), self.assertRaisesRegex(ValueError, "older IPA"):
                generator.ensure_progress(data, previous)

    def test_same_package_is_idempotent_but_another_url_cannot_reuse_its_identity(self):
        data = {"apps": [{"versions": [{"version": "2.1.5506", "buildVersion": "5506", "downloadURL": "current"}]}]}
        generator.ensure_progress(data, data)
        changed = {"apps": [{"versions": [dict(data["apps"][0]["versions"][0], downloadURL="other")]}]}
        with self.assertRaisesRegex(ValueError, "same version and build"):
            generator.ensure_progress(changed, data)

    def generate(self, releases, payload):
        with patch.object(generator, "urlopen", return_value=io.BytesIO(payload)) as download:
            data = generator.generate(self.config, releases)
        return data, download

    def test_metadata_comes_from_binary_plist_not_tag_or_filename(self):
        payload = ipa(CFBundleShortVersionString="2.2.0", CFBundleVersion="6001", MinimumOSVersion="16.2")
        data, _ = self.generate([release(payload=payload)], payload)
        version = data["apps"][0]["versions"][0]
        self.assertEqual((version["version"], version["buildVersion"], version["minOSVersion"]), ("2.2.0", "6001", "16.2"))
        self.assertEqual(data["apps"][0]["bundleIdentifier"], "com.example.piliplus.btr")
        self.assertIn("v2.1.4-btr.15", data["news"][0]["title"])

    def test_stable_filter_and_btr_revision_order_on_same_day(self):
        payload = ipa()
        releases = [
            release(9), release(16, prerelease=True), release(15),
            release(99, name="PiliPlus-BTR-ios14_2.1.4+5419.ipa"),
            release(100, name="PiliPlus-BTR-2.1.4-btr.100-arm64.apk"),
        ]
        data, download = self.generate(releases, payload)
        versions = data["apps"][0]["versions"]
        self.assertEqual(len(versions), 1)
        self.assertIn("btr.15", versions[0]["downloadURL"])
        download.assert_called_once_with(versions[0]["downloadURL"], timeout=60)
        self.assertEqual(len(data["news"]), 1)

    def test_draft_is_excluded(self):
        draft = release(99)
        draft["draft"] = True
        data, _ = self.generate([draft, release()], ipa())
        self.assertIn("btr.15", data["apps"][0]["versions"][0]["downloadURL"])

    def test_personal_sha_tags_keep_numeric_build_order(self):
        older, newer = release(9999), release(10000)
        older["tag_name"] += "-ffffffffffff"
        newer["tag_name"] += "-aaaaaaaaaaaa"
        payload = ipa(CFBundleVersion="10000")
        older["assets"][0]["size"] = newer["assets"][0]["size"] = len(payload)
        older["assets"][0]["digest"] = newer["assets"][0]["digest"] = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        data, _ = self.generate([older, newer], payload)
        self.assertIn("btr.10000", data["apps"][0]["versions"][0]["downloadURL"])
        self.assertIn("v2.1.4-btr.10000-aaaaaaaaaaaa", data["news"][0]["title"])

    def test_wrong_bundle_is_rejected(self):
        payload = ipa(CFBundleIdentifier="com.example.piliplus")
        with self.assertRaisesRegex(ValueError, "bundle identifier"):
            self.generate([release(payload=payload)], payload)

    def test_missing_build_is_rejected(self):
        payload = ipa(CFBundleVersion="")
        with self.assertRaisesRegex(ValueError, "missing build"):
            self.generate([release(payload=payload)], payload)

    def test_corrupt_archive_is_rejected(self):
        with self.assertRaises(IpaError):
            self.generate([release(payload=b"not a zip")], b"not a zip")

    def test_size_and_digest_must_match(self):
        for field, value in (("size", 1), ("digest", "sha256:wrong")):
            with self.subTest(field=field):
                item = release()
                item["assets"][0][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    self.generate([item], ipa())

    def test_failure_preserves_last_good_source(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "apps.json"
            output.write_text("last good source")
            config = replace(self.config, output=replace(self.config.output, path=output))
            with patch.object(generator, "load_config", return_value=config), patch.object(generator, "fetch_releases", return_value=[]):
                with self.assertRaisesRegex(ValueError, "No matching stable"):
                    generator.main()
            self.assertEqual(output.read_text(), "last good source")


if __name__ == "__main__":
    unittest.main()
