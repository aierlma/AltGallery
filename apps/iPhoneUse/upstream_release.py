#!/usr/bin/env python3
"""Resolve and validate an official iphone-use runner release.

This tool is deliberately small and dependency-free so the GitHub workflow can
run it before checking out or building anything.  It validates the formal
release, resolves its tag to a full commit SHA, checks the release assets, and
reads the exact upstream build scripts at that immutable commit.  The emitted
JSON is the hand-off consumed by ``build_candidate.sh``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = "leeguooooo/iphone-use"
API_ROOT = "https://api.github.com/repos"
RAW_ROOT = "https://raw.githubusercontent.com"
TAG_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ASSET_NAMES = {
    "runner_archive": "iphone-use-runner.tar.gz",
    "runner_checksum": "iphone-use-runner.tar.gz.sha256",
}

# These are intentionally checks on the upstream's own scripts.  The build
# workflow invokes these same scripts instead of recreating their build logic.
SOURCE_CHECKS = {
    "runner/build.sh": (
        "--unsigned",
        "build-for-testing",
        "IPU_EMBED_LIB",
        "CODE_SIGNING_ALLOWED=NO",
    ),
    "scripts/build-ios-embed.sh": (
        "aarch64-apple-ios",
        "libipu_embed.a",
        "-p ios-embed",
    ),
    "runner/ci-check.sh": (
        "runner/unit-check.sh",
        "runner/build.sh --unsigned",
    ),
}


class UpstreamError(RuntimeError):
    """An upstream release cannot be used as an input candidate."""


def fetch_json(url: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AltGallery-iPhoneUse-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        url,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
    except (HTTPError, URLError) as error:
        raise UpstreamError(f"GitHub API request failed for {url}: {error}") from error
    if len(raw) > 4 * 1024 * 1024:
        raise UpstreamError(f"GitHub API response is too large: {url}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise UpstreamError(f"GitHub API returned invalid JSON for {url}") from error
    if not isinstance(data, dict):
        raise UpstreamError(f"GitHub API returned a non-object for {url}")
    return data


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "AltGallery-iPhoneUse-updater"})
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError) as error:
        raise UpstreamError(f"upstream source request failed for {url}: {error}") from error
    if len(raw) > 1024 * 1024:
        raise UpstreamError(f"upstream source is too large: {url}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UpstreamError(f"upstream source is not UTF-8: {url}") from error


def release_url(repository: str, tag: str | None) -> str:
    if tag:
        return f"{API_ROOT}/{repository}/releases/tags/{tag}"
    return f"{API_ROOT}/{repository}/releases/latest"


def validate_asset(repository: str, release: dict, name: str) -> dict:
    matches = [item for item in release.get("assets", []) if item.get("name") == name]
    if len(matches) != 1:
        raise UpstreamError(f"formal release must contain exactly one {name}")
    asset = matches[0]
    prefix = f"https://github.com/{repository}/releases/download/"
    if asset.get("state") != "uploaded" or not asset.get("browser_download_url", "").startswith(prefix):
        raise UpstreamError(f"release asset is not an uploaded repository asset: {name}")
    if not isinstance(asset.get("size"), int) or asset["size"] <= 0:
        raise UpstreamError(f"release asset has no positive size: {name}")
    digest = asset.get("digest")
    if digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise UpstreamError(f"release asset has an invalid GitHub digest: {name}")
    return {
        "name": name,
        "url": asset["browser_download_url"],
        "size": asset["size"],
        "digest": digest,
        "id": asset.get("id"),
    }


def resolve(repository: str = DEFAULT_REPOSITORY, tag: str | None = None) -> dict:
    release = fetch_json(release_url(repository, tag))
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise UpstreamError("upstream release is not a formal non-prerelease")
    resolved_tag = release.get("tag_name")
    if not isinstance(resolved_tag, str) or not TAG_RE.fullmatch(resolved_tag):
        raise UpstreamError(f"upstream release tag is not numeric semver: {resolved_tag!r}")
    if tag is not None and tag != resolved_tag:
        raise UpstreamError(f"requested tag {tag!r} resolved to {resolved_tag!r}")

    # GitHub's commits endpoint resolves both lightweight and annotated tags to
    # the commit that actually contains the released source.  A full SHA is the
    # immutable value recorded in candidate metadata and checked out by CI.
    commit_data = fetch_json(f"{API_ROOT}/{repository}/commits/{resolved_tag}")
    commit = commit_data.get("sha")
    if not isinstance(commit, str) or not SHA_RE.fullmatch(commit.lower()):
        raise UpstreamError(f"could not resolve {resolved_tag} to a full commit SHA")
    commit = commit.lower()

    source_urls: dict[str, str] = {}
    source_digests: dict[str, str] = {}
    for path, needles in SOURCE_CHECKS.items():
        url = f"{RAW_ROOT}/{repository}/{commit}/{path}"
        source = fetch_text(url)
        missing = [needle for needle in needles if needle not in source]
        if missing:
            raise UpstreamError(f"upstream {path} is missing expected build markers: {', '.join(missing)}")
        source_urls[path] = url
        source_digests[path] = hashlib.sha256(source.encode("utf-8")).hexdigest()

    archive = validate_asset(repository, release, ASSET_NAMES["runner_archive"])
    checksum = validate_asset(repository, release, ASSET_NAMES["runner_checksum"])
    version = TAG_RE.fullmatch(resolved_tag).group("version")
    return {
        "schema": 1,
        "repository": repository,
        "tag": resolved_tag,
        "version": version,
        "commit": commit,
        "release_id": release.get("id"),
        "release_url": release.get("html_url"),
        "release_published_at": release.get("published_at"),
        "runner_archive": archive,
        "runner_checksum": checksum,
        "source_urls": source_urls,
        "source_sha256": source_digests,
        "checks": {
            "formal_release": True,
            "immutable_commit": True,
            "official_build_scripts": True,
            "unsigned_runner_path": True,
            "embedded_daemon_path": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY, help="upstream owner/repository")
    parser.add_argument("--tag", help="formal tag to resolve instead of the latest release")
    parser.add_argument("--output", type=Path, help="write metadata JSON to this path")
    args = parser.parse_args(argv)
    try:
        data = resolve(args.repo, args.tag)
    except UpstreamError as error:
        print(f"iphone-use upstream check failed: {error}", file=sys.stderr)
        return 1
    encoded = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
