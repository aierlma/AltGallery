#!/usr/bin/env python3
"""Package an existing 0.17.19 XCTest build for SideStore's 0.7 pipeline.

The original build is preserved. The resulting input is ad-hoc signed and must
be re-signed by SideStore. Launch with UseDestinationArtifacts and point
TestBundleDestinationRelativePath at __TESTHOST__/Frameworks/iPhoneUse.xctest.
"""
import argparse
import hashlib
import json
import plistlib
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def run(*args):
    return subprocess.run(args, check=True, capture_output=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built_app", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    original_hash = sha256(args.built_app / "iPhoneUse-Runner")
    with tempfile.TemporaryDirectory(prefix="iphone-use-sidestore-") as directory:
        work = Path(directory)
        payload = work / "Payload"
        payload.mkdir()
        app = payload / "iPhoneUse-Runner.app"
        run("ditto", str(args.built_app), str(app))
        for symbols in app.rglob("*.dSYM"):
            shutil.rmtree(symbols)
        for profile in app.rglob("*.mobileprovision"):
            profile.unlink()
        host_id = "com.leeguoo.iphone-use.runner.xctrunner"
        test = app / "PlugIns/iPhoneUse.xctest"
        for path in (app / "Info.plist", test / "Info.plist"):
            info = plistlib.loads(path.read_bytes())
            info.update(CFBundleIdentifier=host_id, CFBundleShortVersionString="0.17.19", CFBundleVersion="3")
            path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_BINARY))
        # SideStore 0.7 models only .appex as extensions, but installation
        # enumerates all PlugIns bundles. Keep XCTest out of that inconsistent
        # path; CodeSignKit recursively signs .xctest wherever it is embedded.
        frameworks = app / "Frameworks"
        frameworks.mkdir(exist_ok=True)
        destination = frameworks / test.name
        test.rename(destination)
        assert not any((app / "PlugIns").iterdir())
        (app / "PlugIns").rmdir()
        shutil.copyfile(Path(__file__).with_name("LICENSE.iphone-use"), app / "LICENSE.iphone-use")
        # Remove personal certificate identities, entitlements and code seals.
        run("codesign", "--remove-signature", str(destination))
        run("codesign", "--force", "--timestamp=none", "--sign", "-", str(destination))
        run("codesign", "--remove-signature", str(app))
        entitlements = work / "entitlements.plist"
        entitlements.write_bytes(plistlib.dumps({"get-task-allow": True}))
        run("codesign", "--force", "--timestamp=none", "--sign", "-", "--entitlements", str(entitlements), str(app))
        run("codesign", "--verify", "--deep", "--strict", str(app))
        run("codesign", "--verify", "--strict", str(destination))
        assert not list(app.rglob("*.mobileprovision"))
        run("ditto", "-c", "-k", "--norsrc", "--noextattr", "--keepParent", str(payload), str(args.output))
        with zipfile.ZipFile(args.output) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert "Payload/iPhoneUse-Runner.app/Frameworks/iPhoneUse.xctest/iPhoneUse" in names
            assert not any("/PlugIns/" in name or ".dSYM/" in name or "mobileprovision" in name for name in names)
            for name in names:
                if name.endswith("Info.plist"):
                    info = plistlib.loads(archive.read(name))
                    assert "FGV7RZH278" not in str(info).upper()
        assert sha256(args.built_app / "iPhoneUse-Runner") == original_hash
        print(json.dumps({"output": str(args.output), "bytes": args.output.stat().st_size,
                          "sha256": sha256(args.output), "bundle_id": host_id,
                          "test_path": "Frameworks/iPhoneUse.xctest", "build": "3",
                          "status": "local checks passed; device installation and launch pending"}, indent=2))


if __name__ == "__main__":
    main()
