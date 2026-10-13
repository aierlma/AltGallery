"""Regression checks for iPhoneUse release progression."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "iphone_use_generator", ROOT / "apps/iPhoneUse/generate.py"
)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def source(version, build, url="current"):
    return {"apps": [{"versions": [{
        "version": version, "buildVersion": str(build), "downloadURL": url,
    }]}]}


class ProgressTests(unittest.TestCase):
    def test_new_upstream_version_can_reset_package_build(self):
        generator.ensure_progress(source("0.18.0", 1, "next"), source("0.17.19", 3))

    def test_older_version_and_same_version_older_build_are_rejected(self):
        previous = source("0.17.19", 3)
        for version, build in (("0.17.18", 100), ("0.17.19", 2)):
            with self.subTest(version=version, build=build):
                with self.assertRaisesRegex(ValueError, "older IPA"):
                    generator.ensure_progress(source(version, build), previous)

    def test_existing_identity_is_idempotent_but_cannot_change_url(self):
        previous = source("0.17.19", 3)
        generator.ensure_progress(previous, previous)
        with self.assertRaisesRegex(ValueError, "same version and build"):
            generator.ensure_progress(source("0.17.19", 3, "changed"), previous)


if __name__ == "__main__":
    unittest.main()
