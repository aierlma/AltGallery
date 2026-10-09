"""Release/source handoff checks, without downloading or executing an IPA."""

import io
import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import source_sync


WATCH = source_sync.Watch("PiliPlus-BTR", "aierlma/PiliPlus", "com.example.piliplus.btr",
                          r"^PiliPlus-BTR-ios-.*-unsigned\.ipa$", "build-info.json")
URL = "https://github.com/aierlma/PiliPlus/releases/download/test/PiliPlus-BTR-ios-test-unsigned.ipa"
INFO = {"bundle_id": WATCH.bundle, "version": "2.1.5506", "build": "5506",
        "min_os_version": "15.0", "size_bytes": 100, "sha256": "a" * 64}


def release():
    return {"draft": False, "prerelease": False, "assets": [
        {"name": "PiliPlus-BTR-ios-test-unsigned.ipa", "state": "uploaded", "size": 100,
         "digest": "sha256:" + "a" * 64, "browser_download_url": URL},
        {"name": "build-info.json", "state": "uploaded",
         "browser_download_url": "https://github.com/aierlma/PiliPlus/releases/download/test/build-info.json"},
    ]}


def package(watch=WATCH, build="5506"):
    return source_sync.Package(watch, {"version": f"2.1.{build}", "buildVersion": build,
                                      "minOSVersion": "15.0", "size": 100, "downloadURL": URL})


class SourceSyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.target = self.root / "apps/PiliPlus-BTR/apps.json"
        self.target.parent.mkdir(parents=True)
        self.aggregate = self.root / "all-apps.json"
        self.write_package(package())

    def tearDown(self):
        self.directory.cleanup()

    def write_package(self, item):
        app = {"bundleIdentifier": item.watch.bundle, "versions": [item.fields]}
        target = self.root / "apps" / item.watch.app / "apps.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"apps": [app]}))
        existing = json.loads(self.aggregate.read_text()) if self.aggregate.exists() else {"apps": []}
        existing["apps"] = [a for a in existing["apps"] if a["bundleIdentifier"] != item.watch.bundle] + [app]
        self.aggregate.write_text(json.dumps(existing))

    def reconcile(self, item=package(), *, update=True, runner=None):
        with patch.object(source_sync, "load_watches", return_value=[WATCH]), \
             patch.object(source_sync, "published_package", return_value=item), \
             patch.object(source_sync.subprocess, "run", side_effect=runner) as run:
            result = source_sync.reconcile(self.root, update=update)
        return result, run

    def test_current_sources_do_not_run_generator_or_rewrite_files(self):
        previous = (self.target.read_bytes(), self.aggregate.read_bytes())
        result, run = self.reconcile()
        self.assertEqual(result, [])
        run.assert_not_called()
        self.assertEqual(previous, (self.target.read_bytes(), self.aggregate.read_bytes()))

    def test_new_release_runs_only_the_targeted_generator_and_preserves_neighbors(self):
        self.write_package(package(build="5502"))
        neighbor = package(replace(WATCH, app="Other", bundle="com.example.other"), "1")
        self.write_package(neighbor)
        result, run = self.reconcile(runner=lambda *a, **k: self.write_package(package()))
        self.assertEqual(result, [WATCH.app])
        self.assertEqual(run.call_args.args[0], ["bash", str(self.root / "update.sh"), WATCH.app])
        self.assertTrue(source_sync.sources_match(self.root, neighbor))
        self.assertTrue(source_sync.sources_match(self.root, package()))

    def test_stale_aggregate_alone_is_reconciled(self):
        self.aggregate.write_text(json.dumps({"apps": []}))
        _, run = self.reconcile(runner=lambda *a, **k: self.write_package(package()))
        run.assert_called_once()

    def test_missing_or_invalid_standalone_is_reconciled(self):
        for invalid in (None, "not JSON"):
            with self.subTest(invalid=invalid):
                if invalid is None:
                    self.target.unlink()
                else:
                    self.target.write_text(invalid)
                _, run = self.reconcile(runner=lambda *a, **k: self.write_package(package()))
                run.assert_called_once()

    def test_verify_detects_staleness_without_mutating_sources(self):
        self.write_package(package(build="5502"))
        previous = self.target.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "differs"):
            self.reconcile(update=False)
        self.assertEqual(self.target.read_bytes(), previous)

    def test_generation_failure_preserves_last_good_output(self):
        self.write_package(package(build="5502"))
        previous = (self.target.read_bytes(), self.aggregate.read_bytes())
        with self.assertRaisesRegex(RuntimeError, "download failed"):
            self.reconcile(runner=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("download failed")))
        self.assertEqual(previous, (self.target.read_bytes(), self.aggregate.read_bytes()))

    def test_older_producer_response_cannot_downgrade_current_sources(self):
        previous = (self.target.read_bytes(), self.aggregate.read_bytes())
        result, run = self.reconcile(package(build="5502"))
        self.assertEqual(result, [])
        run.assert_not_called()
        self.assertEqual(previous, (self.target.read_bytes(), self.aggregate.read_bytes()))

    def test_older_producer_response_cannot_overwrite_one_newer_source(self):
        self.aggregate.write_text(json.dumps({"apps": []}))
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            self.reconcile(package(build="5502"))
        self.assertTrue(source_sync.source_matches(self.target, package()))

    def test_successful_exit_without_convergence_is_a_failure(self):
        self.write_package(package(build="5502"))
        with self.assertRaisesRegex(RuntimeError, "Standalone or aggregate"):
            self.reconcile()

    def test_release_changed_during_generation_is_rechecked(self):
        self.write_package(package(build="5502"))
        newest = package(build="5508")
        with patch.object(source_sync, "load_watches", return_value=[WATCH]), \
             patch.object(source_sync, "published_package", side_effect=[package(), newest]), \
             patch.object(source_sync.subprocess, "run", side_effect=lambda *a, **k: self.write_package(newest)):
            self.assertEqual(source_sync.reconcile(self.root, update=True), [WATCH.app])

    def test_one_failed_watch_does_not_prevent_another_target_update(self):
        other = replace(WATCH, app="Other", bundle="com.example.other")
        latest = package(other)
        with patch.object(source_sync, "load_watches", return_value=[WATCH, other]), \
             patch.object(source_sync, "published_package", side_effect=[RuntimeError("unavailable"), latest]), \
             patch.object(source_sync.subprocess, "run", side_effect=lambda *a, **k: self.write_package(latest)):
            with self.assertRaisesRegex(RuntimeError, "PiliPlus-BTR: unavailable"):
                source_sync.reconcile(self.root, update=True)
        self.assertTrue(source_sync.sources_match(self.root, latest))

    def test_each_source_field_and_bundle_must_match_the_receipt(self):
        for field in package().fields:
            data = json.loads(self.target.read_text())
            data["apps"][0]["versions"][0][field] = "incorrect"
            self.target.write_text(json.dumps(data))
            self.assertFalse(source_sync.sources_match(self.root, package()))
            self.write_package(package())
        data = json.loads(self.target.read_text())
        data["apps"].append(data["apps"][0])
        self.target.write_text(json.dumps(data))
        self.assertFalse(source_sync.sources_match(self.root, package()))

    def test_receipt_metadata_not_tag_or_filename_supplies_version_and_build(self):
        with patch.object(source_sync, "read_json", side_effect=[release(), INFO]):
            actual = source_sync.published_package(WATCH)
        self.assertEqual(actual.fields, package().fields)

    def test_drafts_prereleases_missing_assets_and_foreign_downloads_are_rejected(self):
        for field in ("draft", "prerelease"):
            data = release()
            data[field] = True
            with patch.object(source_sync, "read_json", return_value=data):
                with self.assertRaisesRegex(ValueError, "formal"):
                    source_sync.published_package(WATCH)
        for mutate in (lambda d: d.update(assets=[]),
                       lambda d: d["assets"][0].update(state="new"),
                       lambda d: d["assets"][1].update(browser_download_url="https://other.example/info.json")):
            data = release()
            mutate(data)
            with patch.object(source_sync, "read_json", return_value=data):
                with self.assertRaises(ValueError):
                    source_sync.published_package(WATCH)

    def test_invalid_metadata_size_or_digest_cannot_trigger_generation(self):
        for field, value in (("bundle_id", "wrong"), ("version", "SNAPSHOT"),
                             ("build", ""), ("min_os_version", ""),
                             ("size_bytes", 99), ("sha256", "b" * 64)):
            info = dict(INFO, **{field: value})
            with self.subTest(field=field), patch.object(source_sync, "read_json", side_effect=[release(), info]):
                with self.assertRaises(ValueError):
                    source_sync.published_package(WATCH)

    def test_api_credentials_are_not_attached_to_release_asset_downloads(self):
        with patch.dict(os.environ, GITHUB_TOKEN="test-token"), \
             patch.object(source_sync, "urlopen", side_effect=lambda *a, **k: io.BytesIO(b"{}")) as fetch:
            source_sync.read_json("https://api.github.com/repos/aierlma/PiliPlus/releases/latest", api=True)
            self.assertEqual(fetch.call_args.args[0].get_header("Authorization"), "Bearer test-token")
            source_sync.read_json("https://github.com/aierlma/PiliPlus/releases/download/tag/build-info.json")
            self.assertIsNone(fetch.call_args.args[0].get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
