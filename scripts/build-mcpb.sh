#!/usr/bin/env bash
# Build dist/parley.mcpb for Smithery and Claude Desktop: the manifest, the entry script and a
# copy of the stdlib-only parley/ package. Usage: scripts/build-mcpb.sh
set -euo pipefail
cd "$(dirname "$0")/.."
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
cp mcpb/manifest.json "$stage/"
mkdir "$stage/server"
cp mcpb/server/main.py "$stage/server/"
cp -R parley "$stage/server/parley"
find "$stage" -name __pycache__ -type d -prune -exec rm -rf {} +
mkdir -p dist
npx --yes @anthropic-ai/mcpb@2.1.2 validate "$stage/manifest.json"
npx --yes @anthropic-ai/mcpb@2.1.2 pack "$stage" dist/parley.mcpb
