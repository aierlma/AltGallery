# iPhoneUse Runner — SideStore compatibility candidate

This is a packaging adaptation of [iphone-use 0.17.19](https://github.com/leeguooooo/iphone-use/tree/47cf89852a1de8f2a6670ef4ae811708621825f4), not an official upstream release. The runner implementation is unchanged. Build 3 has passed local archive, metadata and deep code-seal checks; installation, launch and wireless operation on a real device are pending.

SideStore 0.7.0-20260911.328+6032424a models only `.appex` in `appExtensions`, while its resign/install operations enumerate every bundle under `PlugIns`. An ordinary `.xctest` there produces missing-profile or missing-extension errors. This package moves it to `Frameworks/iPhoneUse.xctest`; the pinned CodeSignKit signer recognizes and recursively signs `.xctest` bundles there.

The IPA contains no personal provisioning profile or development certificate signature. SideStore signs it with the user's account and manages its refresh. The original PolyForm Shield license and required notice are included in the app and this directory.

## Build and launch

Given an upstream 0.17.19 `build-for-testing` product:

```sh
python3 package_runner.py /path/to/iPhoneUse-Runner.app /path/to/iPhoneUse-Runner-0.17.19-SideStore-b3.ipa
```

Use Xcode's documented `UseDestinationArtifacts = true` launch mode so it starts the SideStore-installed app without installing a replacement. Use the actual installed `TestHostBundleIdentifier`, set `TestBundleDestinationRelativePath` to `__TESTHOST__/Frameworks/iPhoneUse.xctest`, and omit the local `TestHostPath`, `TestBundlePath` and `UITargetAppPath`. The Mac launch integration is still being validated. Standard upstream setup installs an Xcode-signed runner and must not be used as a substitute for this integration.

Developer Mode and a mounted Developer Disk Image are required. SideStore refresh does not itself start an XCTest session. No phone UI screenshots are included because the control service has not yet started.
