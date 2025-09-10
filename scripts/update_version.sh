#!/usr/bin/env bash
set -euo pipefail

version="$1"

# pyproject.toml
sed -i "s/^version = \".*\"/version = \"$version\"/" pyproject.toml

# manifest.json
jq --arg ver "$version" '.version = $ver' custom_components/meteocat/manifest.json > tmp.json && mv tmp.json custom_components/meteocat/manifest.json

# version.py
echo "__version__ = \"$version\"" > custom_components/meteocat/version.py

# __init__.py
sed -i "s/^__version__ = \".*\"/__version__ = \"$version\"/" custom_components/meteocat/__init__.py
