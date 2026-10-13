#!/usr/bin/env bash
# Build and validate one immutable upstream iPhoneUse Runner candidate.
#
# This script always uses the upstream unsigned build path. It never reads
# Apple credentials, installs to a phone, or publishes a release. The caller
# decides whether the validated candidate should be uploaded.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

metadata=""
work_dir=""
output_dir=""
package_build=""
source_dir=""

fail() {
    printf 'iphone-use candidate build: %s\n' "$*" >&2
    exit 1
}

usage() {
    sed -n '2,9p' "$0"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --metadata)
            [[ $# -ge 2 ]] || fail "--metadata needs a path"
            metadata="$2"
            shift
            ;;
        --work-dir)
            [[ $# -ge 2 ]] || fail "--work-dir needs a path"
            work_dir="$2"
            shift
            ;;
        --output-dir)
            [[ $# -ge 2 ]] || fail "--output-dir needs a path"
            output_dir="$2"
            shift
            ;;
        --build)
            [[ $# -ge 2 ]] || fail "--build needs a value"
            package_build="$2"
            shift
            ;;
        --source-dir)
            [[ $# -ge 2 ]] || fail "--source-dir needs a path"
            source_dir="$2"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown argument: $1"
            ;;
    esac
    shift
done

[[ -n "$metadata" && -f "$metadata" ]] || fail "--metadata must name a JSON file"
command -v python3 >/dev/null || fail "python3 is required"
command -v git >/dev/null || fail "git is required"
command -v curl >/dev/null || fail "curl is required"
command -v tar >/dev/null || fail "tar is required"

if [[ -z "$work_dir" ]]; then
    work_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/iphone-use-candidate.$$"
fi
if [[ -z "$output_dir" ]]; then
    output_dir="$work_dir/output"
fi
mkdir -p "$work_dir" "$output_dir"

read_metadata() {
    python3 - "$metadata" <<'PY'
import json
import re
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = ("repository", "tag", "version", "commit", "runner_archive", "runner_checksum")
missing = [key for key in required if key not in data]
if missing:
    raise SystemExit("metadata is missing: " + ", ".join(missing))
if not re.fullmatch(r"v\d+\.\d+\.\d+", data["tag"]):
    raise SystemExit("metadata tag is not a release tag")
if not re.fullmatch(r"\d+\.\d+\.\d+", data["version"]):
    raise SystemExit("metadata version is not numeric semver")
if not re.fullmatch(r"[0-9a-f]{40}", data["commit"]):
    raise SystemExit("metadata commit is not a full SHA")
for field in ("runner_archive", "runner_checksum"):
    item = data[field]
    if not isinstance(item, dict) or not item.get("url") or not item.get("name"):
        raise SystemExit(f"metadata {field} is incomplete")
print(data["repository"])
print(data["tag"])
print(data["version"])
print(data["commit"])
print(data["runner_archive"]["url"])
print(data["runner_checksum"]["url"])
PY
}

metadata_values="$(read_metadata)"
repository="$(printf '%s\n' "$metadata_values" | sed -n '1p')"
upstream_tag="$(printf '%s\n' "$metadata_values" | sed -n '2p')"
version="$(printf '%s\n' "$metadata_values" | sed -n '3p')"
commit="$(printf '%s\n' "$metadata_values" | sed -n '4p')"
archive_url="$(printf '%s\n' "$metadata_values" | sed -n '5p')"
checksum_url="$(printf '%s\n' "$metadata_values" | sed -n '6p')"
[[ -n "$repository" && -n "$upstream_tag" && -n "$version" && -n "$commit" && -n "$archive_url" && -n "$checksum_url" ]] \
    || fail "metadata parser returned an unexpected shape"

if [[ -z "$package_build" ]]; then
    # Build 3 is the already verified 0.17.19 SideStore package. New upstream
    # releases start at build 1; the release tag and commit make the package
    # identity idempotent even when upstream reuses a source version.
    if [[ "$version" == "0.17.19" ]]; then
        package_build=3
    else
        package_build=1
    fi
fi
[[ "$package_build" =~ ^[1-9][0-9]*$ ]] || fail "package build must be a positive integer"

if [[ -z "$source_dir" ]]; then
    source_dir="$work_dir/upstream"
fi
if [[ -e "$source_dir" ]]; then
    [[ -d "$source_dir/.git" ]] || fail "source directory exists but is not a Git checkout: $source_dir"
else
    mkdir -p "$source_dir"
    git -C "$source_dir" init -q
    git -C "$source_dir" remote add origin "https://github.com/$repository.git"
fi
git -C "$source_dir" fetch --quiet --depth=1 origin "$commit"
git -C "$source_dir" checkout --quiet --detach "$commit"
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$commit" ]] \
    || fail "checkout did not resolve to the immutable upstream commit"

for path in runner/build.sh scripts/build-ios-embed.sh runner/ci-check.sh; do
    [[ -f "$source_dir/$path" ]] || fail "upstream checkout is missing $path"
done

# Download the official runner archive and its official checksum asset. The
# archive is evidence that the release includes the expected runner product;
# the build itself intentionally comes from the source checkout above so the
# source and scripts are pinned to the same commit.
archive="$work_dir/iphone-use-runner.tar.gz"
checksum="$work_dir/iphone-use-runner.tar.gz.sha256"
curl --fail --location --retry 3 --retry-delay 1 --silent --show-error \
    "$archive_url" -o "$archive"
curl --fail --location --retry 3 --retry-delay 1 --silent --show-error \
    "$checksum_url" -o "$checksum"

hash_file() {
    if command -v shasum >/dev/null; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        sha256sum "$1" | awk '{print $1}'
    fi
}

archive_hash="$(hash_file "$archive")"
checksum_hash="$(awk '$2 == "iphone-use-runner.tar.gz" || $2 == "*iphone-use-runner.tar.gz" {print $1; exit}' "$checksum")"
[[ "$checksum_hash" =~ ^[0-9a-fA-F]{64}$ ]] \
    || fail "official checksum asset has no iphone-use-runner.tar.gz digest"
archive_hash_lower="$(printf '%s' "$archive_hash" | tr '[:upper:]' '[:lower:]')"
checksum_hash_lower="$(printf '%s' "$checksum_hash" | tr '[:upper:]' '[:lower:]')"
[[ "$archive_hash_lower" == "$checksum_hash_lower" ]] \
    || fail "runner archive failed the official checksum asset"

expected_digest="$(python3 - "$metadata" <<'PY'
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["runner_archive"].get("digest")
print(value.removeprefix("sha256:") if isinstance(value, str) else "")
PY
)"
if [[ -n "$expected_digest" ]]; then
    expected_digest_lower="$(printf '%s' "$expected_digest" | tr '[:upper:]' '[:lower:]')"
    [[ "$archive_hash_lower" == "$expected_digest_lower" ]] \
        || fail "runner archive failed GitHub's immutable asset digest"
fi

archive_root="$work_dir/release-archive"
mkdir -p "$archive_root"
while IFS= read -r entry; do
    case "$entry" in
        runner/*) ;;
        *) fail "official runner archive contains an unexpected path: $entry" ;;
    esac
    case "$entry" in
        *../*|*/..|../*) fail "official runner archive contains a traversal path: $entry" ;;
    esac
done < <(tar -tzf "$archive")
tar -xzf "$archive" -C "$archive_root"
[[ -f "$archive_root/runner/IPhoneUseRunner/IPhoneUseRunner.xcodeproj/project.pbxproj" ]] \
    || fail "official runner archive has no generated Xcode project"
[[ -f "$archive_root/runner/embed/libipu_embed.a" ]] \
    || fail "official runner archive has no embedded daemon library"
cmp -s "$archive_root/runner/IPhoneUseRunner/project.yml" \
    "$source_dir/runner/IPhoneUseRunner/project.yml" \
    || fail "official runner archive project differs from the resolved source commit"

# Reuse the upstream's device-independent runner checks before packaging.
bash "$source_dir/runner/unit-check.sh"

# Build the embedded on-phone daemon through the exact upstream script. Its
# exported symbols are checked before the runner is linked so the feature is
# never silently omitted from the candidate.
if command -v rustup >/dev/null; then
    rustup target add aarch64-apple-ios >/dev/null
fi
embed_log="$work_dir/build-ios-embed.stdout"
IPHONEOS_DEPLOYMENT_TARGET=15.0 IPU_EMBED_TARGET_DIR="$work_dir/cargo-target" \
    bash "$source_dir/scripts/build-ios-embed.sh" >"$embed_log"
embed_lib="$(tail -n 1 "$embed_log")"
[[ -f "$embed_lib" ]] || fail "upstream daemon build did not produce a static library"
if command -v lipo >/dev/null; then
    lipo -info "$embed_lib" | grep -q arm64 || fail "daemon library has no arm64 slice"
fi
symbols="$work_dir/embed-symbols.txt"
nm -gU "$embed_lib" >"$symbols" 2>/dev/null || true
grep -q '_ipu_daemon_start$' "$symbols" || fail "daemon library lacks _ipu_daemon_start"
grep -q '_ipu_daemon_pair_code$' "$symbols" || fail "daemon library lacks _ipu_daemon_pair_code"

derived="$work_dir/DerivedData"
runner_log="$work_dir/build-runner.stdout"
IPU_RUNNER_DERIVED_DATA="$derived" IPU_EMBED_LIB="$embed_lib" \
    bash "$source_dir/runner/build.sh" --unsigned >"$runner_log"
xctestrun="$(tail -n 1 "$runner_log")"
[[ -f "$xctestrun" ]] || fail "upstream unsigned build did not produce an .xctestrun"

product="$derived/Build/Products/Debug-iphoneos/iPhoneUse-Runner.app"
if [[ ! -d "$product" ]]; then
    products="$(find "$derived/Build/Products" -type d -name '*-Runner.app' -prune -print)"
    product_count="$(printf '%s\n' "$products" | sed '/^$/d' | wc -l | tr -d ' ')"
    [[ "$product_count" -eq 1 ]] || fail "could not locate exactly one upstream Runner.app product"
    product="$(printf '%s\n' "$products" | sed -n '1p')"
fi

nm -gU "$product/PlugIns/iPhoneUse.xctest/iPhoneUse" >"$work_dir/runner-symbols.txt" 2>/dev/null
grep -q '_ipu_daemon_start$' "$work_dir/runner-symbols.txt" \
    || fail "linked XCTest runner is missing the embedded daemon"

ipa="$output_dir/iPhoneUse-Runner-${version}-SideStore-b${package_build}.ipa"
[[ ! -e "$ipa" ]] || fail "candidate output already exists: $ipa"
package_json="$work_dir/package.json"
python3 "$SCRIPT_DIR/package_runner.py" "$product" "$ipa" \
    --version "$version" --build "$package_build" \
    --license "$source_dir/LICENSE" \
    --upstream-tag "$upstream_tag" --upstream-commit "$commit" >"$package_json"

# Re-read the final archive through the repository's stdlib IPA parser and
# validate the exact SideStore layout before handing it to the publisher.
ipa_info="$work_dir/ipa-info.json"
python3 "$ROOT/tools/ipa_bundle_id.py" "$ipa" --json >"$ipa_info"
python3 - "$ipa_info" "$ipa" "$version" "$package_build" <<'PY'
import json
import sys
import zipfile
from pathlib import Path

info = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ipa = Path(sys.argv[2])
if info.get("bundle_id") != "com.leeguoo.iphone-use.runner.xctrunner":
    raise SystemExit(f"unexpected packaged bundle ID: {info.get('bundle_id')}")
if info.get("version") != sys.argv[3] or info.get("build") != sys.argv[4]:
    raise SystemExit("packaged IPA version/build differs from the candidate metadata")
with zipfile.ZipFile(ipa) as archive:
    names = archive.namelist()
    if archive.testzip() is not None:
        raise SystemExit("packaged IPA failed ZIP CRC validation")
    if not any("Frameworks/iPhoneUse.xctest/iPhoneUse" in name for name in names):
        raise SystemExit("packaged IPA is missing the embedded XCTest executable")
    if any("/PlugIns/" in name or name.endswith(".mobileprovision") for name in names):
        raise SystemExit("packaged IPA still has PlugIns or a provisioning profile")
PY

candidate_json="$output_dir/candidate.json"
python3 - "$metadata" "$package_json" "$ipa_info" "$candidate_json" "$archive_hash" "$package_build" <<'PY'
import json
import sys
from pathlib import Path

upstream = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
package = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
ipa = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
candidate = {
    "schema": 1,
    "upstream": {
        "repository": upstream["repository"],
        "tag": upstream["tag"],
        "commit": upstream["commit"],
        "release_url": upstream.get("release_url"),
        "runner_archive_sha256": sys.argv[5],
    },
    "package": {
        "version": package["version"],
        "build": sys.argv[6],
        "bundle_id": package["bundle_id"],
        "ipa": Path(package["output"]).name,
        "ipa_sha256": package["sha256"],
        "ipa_size": package["bytes"],
        "test_path": package["test_path"],
        "min_os_version": ipa["min_os_version"],
    },
    "validation": {
        "upstream_release_and_scripts": "passed",
        "embedded_daemon_symbols": "passed",
        "unsigned_xcode_build": "passed",
        "runner_logic_and_linked_daemon": "passed",
        "ipa_structure_and_codesign": "passed",
        "device_installation_launch_and_wireless": "not_claimed_by_ci",
    },
}
Path(sys.argv[4]).write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(candidate, indent=2, sort_keys=True))
PY
printf '%s\n' "$candidate_json"
