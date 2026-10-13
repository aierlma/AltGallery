# iPhoneUse Runner — SideStore compatibility candidate

This directory packages the device runner from [iphone-use](https://github.com/leeguooooo/iphone-use) for SideStore. It is an experimental compatibility package, not an official upstream release. The runner implementation and the embedded on-phone daemon come from the immutable upstream release commit selected by the updater.

The published 0.17.19 build 3 is the verified baseline. SideStore 0.7 lists it in My Apps with the expected Runner build, and refresh progressed to 20% before returning `7 DAYS` without an alert. The Mac launch path uses Xcode `UseDestinationArtifacts`; the Runner was launched on the real device, and both USB and encrypted CoreDevice Wi-Fi `phone_reconnect` screenshot reads returned real device pixels. The local launcher is on demand: login or background autonomous Runner start is not enabled, keepalive and `runatload` remain false, and prewarm is disabled.

SideStore 0.7 models `.appex` entries in `appExtensions`, while its resign/install operations enumerate every bundle under `PlugIns`. An ordinary `.xctest` there can produce missing-profile or missing-extension errors. The package therefore moves `iPhoneUse.xctest` to `Frameworks/iPhoneUse.xctest`; the pinned CodeSignKit signer recognizes and recursively signs the XCTest bundle there. The IPA contains no personal provisioning profile or development certificate signature. SideStore signs it with the user's account and manages refresh. The original PolyForm Shield license and required notice are included in the app and this directory.

## Automated updates

`.github/workflows/iphone-use-update.yml` checks the latest formal upstream release hourly and on manual dispatch. It resolves the tag to a full commit SHA, reads the upstream `runner/build.sh`, `runner/ci-check.sh`, and `scripts/build-ios-embed.sh` at that commit, verifies the official runner archive checksum, builds `libipu_embed.a` through the upstream script, and runs the upstream unsigned `build-for-testing` path. `package_runner.py` then makes an ad-hoc signed IPA and validates its metadata, code seal, archive CRC, and relocated XCTest bundle.

The workflow publishes a prerelease only after every check succeeds, with the upstream tag and commit recorded in both the release notes and `candidate.json`. A failed check never changes or replaces the last working release. Successful publication dispatches the existing `update.yml` source generator. Device installation, launch, and wireless operation are not claimed for future candidates until separately verified.

For a real CI build without creating a release, use **Run workflow**, set `dry_run` to `true`, and optionally set `upstream_tag` (for example `v0.17.19`). The artifact contains the IPA and its machine-readable validation metadata. `force` rebuilds an existing candidate for testing but still never overwrites an existing release.

## Local packaging

Given an upstream `build-for-testing` product:

```sh
python3 package_runner.py /path/to/iPhoneUse-Runner.app /path/to/iPhoneUse-Runner-0.17.19-SideStore-b3.ipa
```

The version and build default to the product's `Info.plist`; use `--version` and `--build` when the product was compiled from an upstream release whose marketing metadata differs. The original positional command remains compatible with the verified b3 packager. Use `--test-bundle` only when the product contains more than one XCTest bundle.

Use Xcode's documented `UseDestinationArtifacts = true` launch mode so it starts the SideStore-installed app without installing a replacement. Set `TestBundleDestinationRelativePath` to `__TESTHOST__/Frameworks/iPhoneUse.xctest`, use the actual installed `TestHostBundleIdentifier`, and omit the local `TestHostPath`, `TestBundlePath`, and `UITargetAppPath`. Developer Mode and a mounted Developer Disk Image are required. SideStore refresh does not itself start an XCTest session.
