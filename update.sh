#!/usr/bin/env bash
# AltGallery — regenerate every app source, then merge them into the repo-root all-apps.json.
# Run: ./update.sh  (from anywhere; paths resolve against this script's directory)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Regenerate each <AppName>/apps.json from its config.toml
apps=()
for app_dir in */; do
  if [[ -f "$app_dir/config.toml" ]]; then
    name="${app_dir%/}"
    echo "==> Updating $name"
    (cd "$app_dir" && uvx altgen -c config.toml)
    apps+=("$app_dir/apps.json")
  fi
done

# 2. Merge every generated source into the repo-root all-apps.json
if [[ ${#apps[@]} -gt 0 ]]; then
  echo "==> Merging ${#apps[@]} source(s) into all-apps.json"
  uvx altgen merge -c assets/merge.toml "${apps[@]}"
else
  echo "No app sources found — nothing to merge."
fi
