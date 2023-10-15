#!/bin/bash
# -----------------------------------------------------------------------------
# es7s/core
# (C) 2023 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
# Script for extracting commits from the original repo into separate one.

# shellcheck disable=SC2086
# shellcheck disable=SC2046

set -e

SELF="$(realpath "${BASH_SOURCE[0]}")"
PATHS_TO_DELETE="$(cat <<-EOL
	es7s/shared/*
	es7s/shared/io.py
	es7s/shared/indic_icon.py
	es7s/shared/config.py
	es7s/shared/sun_calc.py
	es7s/shared/prefixed_unit.py
	es7s/shared/color.py
	es7s/commons/ipc.py
	es7s/shared/weather_icons.orig.py
	es7s/shared/proxy.py
	es7s/commons/git.py
	es7s/shared/demo.py
	es7s/shared/regex_url.py
EOL
)"

SRC_PATH=/tmp/gfr-es7s-commons/

rm -rf "$SRC_PATH"
mkdir -p "$SRC_PATH"
gh repo clone es7s/core "$SRC_PATH" -- --branch dev
pushd "$SRC_PATH" || exit
commits_before=$(git log --oneline | wc -l)

git-filter-repo --commit-callback 'commit.message = b"[es7s/core]["+commit.original_id[:8]+b"] "+commit.message'
git-filter-repo --path es7s/commons/ --path es7s/shared
git-filter-repo $(printf -- '--path %s ' $PATHS_TO_DELETE es7s/shared/*) --invert-paths
git tag --delete $(git tag --list) &>/dev/null
commits_after=$(git log --oneline | wc -l)

mkdir misc -p
cp "$SELF" misc/
popd

printf '%80s\n' '' | tr ' ' =
printf "%s\n" "$SRC_PATH"
printf "%-14s: %5d\n" "Commits before" "$commits_before" "Commits after" "$commits_after"

set +e
