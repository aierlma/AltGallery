"""Reconcile verified release metadata with standalone and aggregate sources."""

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Watch:
    app: str
    repo: str
    bundle: str
    asset_pattern: str
    metadata_asset: str


@dataclass(frozen=True)
class Package:
    watch: Watch
    fields: dict


def load_watches(root=ROOT):
    entries = tomllib.loads((root / "assets/source-watch.toml").read_text())["watch"]
    watches = []
    for entry in entries:
        app = entry["app"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_-]*", app):
            raise ValueError("Invalid watched app directory")
        config = tomllib.loads((root / "apps" / app / "config.toml").read_text())
        repo = config["github"]["repo"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Invalid watched GitHub repository")
        watches.append(Watch(app, repo, config["app"]["bundle_identifier"],
                             config["versions"]["asset_pattern"], entry["metadata_asset"]))
    if len({watch.app for watch in watches}) != len(watches):
        raise ValueError("Duplicate watched app")
    return watches


def read_json(url, *, api=False):
    headers = {"User-Agent": "AltGallery-source-sync"}
    if api:
        if not url.startswith("https://api.github.com/repos/"):
            raise ValueError("Refusing to send an API token outside GitHub")
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        content = response.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise ValueError("Release metadata response is too large")
    return json.loads(content)


def published_package(watch):
    release = read_json(f"https://api.github.com/repos/{watch.repo}/releases/latest", api=True)
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("Expected a formal release")
    assets = release.get("assets", [])
    packages = [a for a in assets if re.fullmatch(watch.asset_pattern, a.get("name", ""))]
    metadata = [a for a in assets if a.get("name") == watch.metadata_asset]
    if len(packages) != 1 or len(metadata) != 1:
        raise ValueError("Release must contain one matching IPA and metadata asset")
    asset, manifest = packages[0], metadata[0]
    prefix = f"https://github.com/{watch.repo}/releases/download/"
    for item in (asset, manifest):
        if item.get("state") != "uploaded" or not item.get("browser_download_url", "").startswith(prefix):
            raise ValueError("Release asset is unavailable or outside the producer repository")
    info = read_json(manifest["browser_download_url"])
    if info.get("bundle_id") != watch.bundle:
        raise ValueError("Release metadata has a different bundle identifier")
    if not isinstance(info.get("version"), str) or not re.fullmatch(r"\d+\.\d+\.\d+", info["version"]):
        raise ValueError("Release metadata lacks a numeric iOS version")
    if not isinstance(info.get("build"), str) or not re.fullmatch(r"[1-9]\d*", info["build"]):
        raise ValueError("Release metadata lacks an actual build number")
    if not isinstance(info.get("min_os_version"), str) or not re.fullmatch(r"\d+(?:\.\d+){1,2}", info["min_os_version"]):
        raise ValueError("Release metadata lacks a minimum iOS version")
    size = info.get("size_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size != asset.get("size"):
        raise ValueError("Release metadata size differs from the IPA asset")
    digest = info.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Release metadata lacks a SHA-256 digest")
    if asset.get("digest") and asset["digest"] != f"sha256:{digest}":
        raise ValueError("Release metadata digest differs from the IPA asset")
    return Package(watch, {"version": info["version"], "buildVersion": info["build"],
                           "minOSVersion": info["min_os_version"], "size": size,
                           "downloadURL": asset["browser_download_url"]})


def source_matches(path, package):
    try:
        data = json.loads(path.read_text())
        apps = [app for app in data["apps"] if app["bundleIdentifier"] == package.watch.bundle]
        if len(apps) != 1:
            return False
        return any(all(version.get(key) == value for key, value in package.fields.items())
                   for version in apps[0]["versions"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def sources_match(root, package):
    return all(source_matches(path, package) for path in (
        root / "apps" / package.watch.app / "apps.json", root / "all-apps.json"))


def newer_source(root, package):
    """Keep newer generated packages when the producer API returns older data."""
    expected = (tuple(map(int, package.fields["version"].split("."))),
                int(package.fields["buildVersion"]))
    ahead = []
    for path in (root / "apps" / package.watch.app / "apps.json", root / "all-apps.json"):
        try:
            apps = [a for a in json.loads(path.read_text())["apps"] if a["bundleIdentifier"] == package.watch.bundle]
            if len(apps) != 1:
                continue
            value = apps[0]["versions"][0]
            actual = (tuple(map(int, value["version"].split("."))), int(value["buildVersion"]))
            if actual[0] >= expected[0] and actual[1] >= expected[1] and actual != expected:
                ahead.append({key: value[key] for key in package.fields})
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            continue
    if not ahead:
        return False
    if len(ahead) == 2 and ahead[0] == ahead[1]:
        return True
    raise ValueError("One source is newer than producer metadata; refusing to overwrite it")


def reconcile(root=ROOT, *, update=False):
    failures = []
    updated = []
    for watch in load_watches(root):
        try:
            package = published_package(watch)
            if sources_match(root, package):
                print(f"{watch.app}: both sources match released build {package.fields['buildVersion']}; no update")
                continue
            if newer_source(root, package):
                print(f"{watch.app}: both sources are newer than producer metadata; keeping them")
                continue
            if update:
                # Reuse actual-IPA validation and the existing per-app failure policy.
                subprocess.run(["bash", str(root / "update.sh"), watch.app], cwd=root, check=True)
                updated.append(watch.app)
            if not sources_match(root, package):
                # A producer can publish another release while generation is running.
                package = published_package(watch)
                if not sources_match(root, package) and not newer_source(root, package):
                    raise ValueError("Standalone or aggregate source differs from the published IPA metadata")
            print(f"{watch.app}: verified both sources at build {package.fields['buildVersion']}")
        except Exception as error:
            failures.append(f"{watch.app}: {error}")
    if failures:
        raise RuntimeError("\n".join(failures))
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("watch", "verify"))
    args = parser.parse_args()
    try:
        reconcile(update=args.mode == "watch")
    except Exception as error:
        print(f"Source sync failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
