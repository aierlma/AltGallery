# /// script
# requires-python = ">=3.11"
# dependencies = ["altgen==0.2.7"]
# ///
"""Generate with AltGen, using the downloaded stable IPA's actual metadata."""

import hashlib
import os
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

from altgen.config import load_config
from altgen.github import fetch_releases
from altgen.source import build_source, serialize

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from ipa_bundle_id import read_ipa


def download_ipa(asset, path):
    # Only the public asset URL is fetched; never send the API token to a CDN.
    digest = hashlib.sha256()
    with urlopen(asset["browser_download_url"], timeout=60) as response, path.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    if path.stat().st_size != asset["size"]:
        raise ValueError("IPA size does not match the release asset")
    expected = asset.get("digest")
    if expected and expected != f"sha256:{digest.hexdigest()}":
        raise ValueError("IPA digest does not match the release asset")


def generate(config, releases):
    data = build_source(config, releases)
    versions = data["apps"][0]["versions"]
    if not versions:
        raise ValueError("No matching stable BTR IPA; keeping the previous source")
    assets = {
        asset["browser_download_url"]: asset
        for release in releases
        for asset in release.get("assets", [])
    }
    with tempfile.TemporaryDirectory(prefix="piliplus-btr-") as directory:
        for version in versions:
            asset = assets[version["downloadURL"]]
            path = Path(directory) / "release.ipa"
            download_ipa(asset, path)
            metadata = read_ipa(path)
            if metadata["bundle_id"] != config.app.bundle_identifier:
                raise ValueError(f"Unexpected IPA bundle identifier: {metadata['bundle_id']}")
            for key in ("version", "build", "min_os_version"):
                if not isinstance(metadata[key], str) or not metadata[key].strip():
                    raise ValueError(f"IPA is missing {key}")
            version.update(
                version=metadata["version"],
                buildVersion=metadata["build"],
                minOSVersion=metadata["min_os_version"],
                size=metadata["size_bytes"],
            )
    return data


def main():
    config = load_config(Path(__file__).with_name("config.toml"))
    releases = fetch_releases(config.github.repo, os.environ.get("GITHUB_TOKEN") or config.github.token)
    data = generate(config, releases)
    # Publish only after every selected IPA validates; preserve last good output on failure.
    output = config.output.path
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, delete=False) as temporary:
        temporary.write(serialize(data))
    Path(temporary.name).replace(output)
    version = data["apps"][0]["versions"][0]
    print(f"Wrote {output} (version {version['version']}, build {version['buildVersion']}, iOS {version['minOSVersion']}+)")


if __name__ == "__main__":
    main()
