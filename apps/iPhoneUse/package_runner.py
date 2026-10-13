#!/usr/bin/env python3
"""Package an upstream XCTest runner for SideStore.

The input is an unsigned or development-signed ``*-Runner.app`` product from
the upstream ``build-for-testing`` path.  The XCTest bundle is moved from
``PlugIns`` to ``Frameworks`` because SideStore 0.7 enumerates those two
locations inconsistently.  The resulting archive is ad-hoc signed and must be
re-signed by SideStore before installation.

The two positional arguments are intentionally unchanged from the original
0.17.19 packager.  Version and build default to the product's Info.plist and
can be overridden for a release package with ``--version`` and ``--build``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


HOST_BUNDLE_ID = "com.leeguoo.iphone-use.runner.xctrunner"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
BUILD_RE = re.compile(r"^[1-9]\d*(?:\.\d+)*$")


def run(*args: str | Path) -> subprocess.CompletedProcess[bytes]:
    """Run a packaging command without exposing its output by default."""

    return subprocess.run(args, check=True, capture_output=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_plist(path: Path) -> dict:
    try:
        value = plistlib.loads(path.read_bytes())
    except (OSError, plistlib.InvalidFileException) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a property-list dictionary")
    return value


def write_plist(path: Path, value: dict) -> None:
    path.write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_BINARY))


def executable_path(app: Path, info: dict) -> Path:
    name = info.get("CFBundleExecutable")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{app} has no CFBundleExecutable")
    path = app / name
    if not path.is_file():
        raise ValueError(f"{app} is missing its executable {name}")
    return path


def locate_test_bundle(app: Path, requested: str | None) -> tuple[Path, str]:
    """Find the XCTest bundle without silently dropping another plug-in."""

    if requested:
        candidate = app / requested
        if not candidate.is_dir():
            raise ValueError(f"requested XCTest bundle does not exist: {requested}")
        if candidate.suffix != ".xctest":
            raise ValueError(f"requested test bundle is not an .xctest: {requested}")
        return candidate, requested

    plug_ins = app / "PlugIns"
    candidates = sorted(path for path in plug_ins.glob("*.xctest") if path.is_dir())
    if len(candidates) == 1:
        return candidates[0], str(candidates[0].relative_to(app))
    if len(candidates) > 1:
        names = ", ".join(str(path.relative_to(app)) for path in candidates)
        raise ValueError(f"multiple XCTest bundles found; pass --test-bundle ({names})")

    # This keeps the packager idempotent for the already packaged, verified b3
    # artifact while still rejecting a product that has no test bundle.
    framework_candidates = sorted(
        path for path in (app / "Frameworks").glob("*.xctest") if path.is_dir()
    )
    if len(framework_candidates) == 1:
        return framework_candidates[0], str(framework_candidates[0].relative_to(app))
    if len(framework_candidates) > 1:
        names = ", ".join(str(path.relative_to(app)) for path in framework_candidates)
        raise ValueError(f"multiple Frameworks XCTest bundles found ({names})")
    raise ValueError(f"{app} has no XCTest bundle in PlugIns or Frameworks")


def remove_signature(path: Path) -> None:
    """Remove an existing signature, accepting an intentionally unsigned input."""

    try:
        run("codesign", "--remove-signature", str(path))
    except subprocess.CalledProcessError as error:
        # ``build.sh --unsigned`` is the CI input.  codesign exits non-zero for
        # an object that has no signature; any other failure remains fatal.
        detail = (error.stderr or b"").decode(errors="replace").lower()
        if "not signed" not in detail and "code object is not signed" not in detail:
            raise


def validate_version(version: str, build: str) -> None:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"version must be numeric semver (got {version!r})")
    if not BUILD_RE.fullmatch(build):
        raise ValueError(f"build must be a positive numeric value (got {build!r})")


def package(args: argparse.Namespace) -> dict:
    built_app = args.built_app
    output = args.output
    if not built_app.is_dir() or built_app.suffix != ".app":
        raise ValueError(f"built_app must be an .app directory: {built_app}")
    if output.exists():
        raise FileExistsError(output)

    input_info = read_plist(built_app / "Info.plist")
    input_executable = executable_path(built_app, input_info)
    input_version = input_info.get("CFBundleShortVersionString")
    input_build = input_info.get("CFBundleVersion")
    version = args.version or input_version
    build = args.build or input_build
    if not isinstance(version, str) or not isinstance(build, str):
        raise ValueError("input Info.plist must contain CFBundleShortVersionString and CFBundleVersion")
    validate_version(version, build)

    original_hash = sha256(input_executable)
    _, source_test_relative = locate_test_bundle(built_app, args.test_bundle)
    host_id = args.bundle_id or HOST_BUNDLE_ID
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host_id):
        raise ValueError(f"invalid bundle identifier: {host_id!r}")

    with tempfile.TemporaryDirectory(prefix="iphone-use-sidestore-") as directory:
        work = Path(directory)
        payload = work / "Payload"
        payload.mkdir()
        app = payload / built_app.name
        run("ditto", str(built_app), str(app))

        for symbols in app.rglob("*.dSYM"):
            shutil.rmtree(symbols)
        for profile in app.rglob("*.mobileprovision"):
            profile.unlink()

        test = app / source_test_relative
        test_info_path = test / "Info.plist"
        if not test_info_path.is_file():
            raise ValueError(f"XCTest bundle is missing Info.plist: {source_test_relative}")
        test_info = read_plist(test_info_path)
        app_info = read_plist(app / "Info.plist")
        for info in (app_info, test_info):
            info.update(
                CFBundleIdentifier=host_id,
                CFBundleShortVersionString=version,
                CFBundleVersion=build,
            )
        write_plist(app / "Info.plist", app_info)
        write_plist(test_info_path, test_info)

        plug_ins = app / "PlugIns"
        if test.parent == plug_ins:
            frameworks = app / "Frameworks"
            frameworks.mkdir(exist_ok=True)
            destination = frameworks / test.name
            if destination.exists():
                raise ValueError(f"destination XCTest bundle already exists: {destination}")
            test.rename(destination)
            remaining = [path for path in plug_ins.iterdir()]
            if remaining:
                names = ", ".join(path.name for path in remaining)
                raise ValueError(f"unsupported extra PlugIns entries; refusing to drop: {names}")
            plug_ins.rmdir()
        elif test.parent == app / "Frameworks":
            destination = test
        else:
            raise ValueError(f"XCTest bundle must be directly under PlugIns or Frameworks: {source_test_relative}")

        license_path = args.license or Path(__file__).with_name("LICENSE.iphone-use")
        if not license_path.is_file():
            raise ValueError(f"missing license notice: {license_path}")
        shutil.copyfile(license_path, app / "LICENSE.iphone-use")

        # Remove personal signing material, then create the ad-hoc signatures
        # which SideStore can replace with the user's own identity.
        remove_signature(destination)
        run("codesign", "--force", "--timestamp=none", "--sign", "-", str(destination))
        remove_signature(app)
        entitlements = work / "entitlements.plist"
        entitlements.write_bytes(plistlib.dumps({"get-task-allow": True}))
        run(
            "codesign",
            "--force",
            "--timestamp=none",
            "--sign",
            "-",
            "--entitlements",
            str(entitlements),
            str(app),
        )
        run("codesign", "--verify", "--deep", "--strict", str(app))
        run("codesign", "--verify", "--strict", str(destination))
        if list(app.rglob("*.mobileprovision")):
            raise ValueError("provisioning profile remained in packaged app")

        output.parent.mkdir(parents=True, exist_ok=True)
        run(
            "ditto",
            "-c",
            "-k",
            "--norsrc",
            "--noextattr",
            "--keepParent",
            str(payload),
            str(output),
        )

        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("packaged IPA failed ZIP CRC validation")
            names = archive.namelist()
            expected_test = f"Payload/{app.name}/Frameworks/{destination.name}/"
            if not any(name.startswith(expected_test) for name in names):
                raise ValueError("packaged IPA does not contain the relocated XCTest bundle")
            if any("/PlugIns/" in name or ".dSYM/" in name or name.endswith(".mobileprovision") for name in names):
                raise ValueError("packaged IPA contains unsupported PlugIns, dSYM, or provisioning material")
            for name in names:
                if name.endswith("Info.plist"):
                    info = plistlib.loads(archive.read(name))
                    if "FGV7RZH278" in str(info).upper():
                        raise ValueError("packaged IPA contains the old personal signing team identifier")

        if sha256(input_executable) != original_hash:
            raise ValueError("input runner executable changed during packaging")

    return {
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "bundle_id": host_id,
        "version": version,
        "build": build,
        "test_path": f"Frameworks/{destination.name}",
        "upstream_tag": args.upstream_tag,
        "upstream_commit": args.upstream_commit,
        "status": "local checks passed; device installation and launch require separate validation",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built_app", type=Path, help="upstream *-Runner.app product")
    parser.add_argument("output", type=Path, help="output .ipa; it must not already exist")
    parser.add_argument("--version", help="override CFBundleShortVersionString")
    parser.add_argument("--build", help="override CFBundleVersion")
    parser.add_argument("--bundle-id", default=HOST_BUNDLE_ID, help="normalized host/test bundle ID")
    parser.add_argument(
        "--test-bundle",
        help="path to the .xctest relative to the app (otherwise discover exactly one)",
    )
    parser.add_argument("--license", type=Path, help="license notice to include in the app")
    parser.add_argument("--upstream-tag", help="resolved upstream release tag for output metadata")
    parser.add_argument("--upstream-commit", help="resolved upstream commit for output metadata")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = package(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
