#!/bin/bash
# Roll the `current` symlink back to a previous release (security hardening
# Phase 4). Usage:
#   rollback.sh              -> newest release older than the current one
#   rollback.sh <version>    -> that exact release
#   rollback.sh --list       -> list releases, '*' marks current
set -euo pipefail

RELEASES_DIR="${RELEASES_DIR:-$HOME/releases/idx-walkforward}"
CURRENT_LINK="${CURRENT_LINK:-$HOME/idx-walkforward-current}"

current_target=""
[ -L "$CURRENT_LINK" ] && current_target=$(readlink -f "$CURRENT_LINK")
current_version=$(basename "${current_target:-none}")

if [ "${1:-}" = "--list" ]; then
    for d in $(ls -1 "$RELEASES_DIR" | sort); do
        marker=" "
        [ "$d" = "$current_version" ] && marker="*"
        echo "$marker $d"
    done
    exit 0
fi

if [ -n "${1:-}" ]; then
    TARGET="$1"
else
    TARGET=$(ls -1 "$RELEASES_DIR" | sort | awk -v cur="$current_version" \
        '$0 == cur {exit} {prev=$0} END {print prev}')
fi

if [ -z "$TARGET" ] || [ ! -d "$RELEASES_DIR/$TARGET" ]; then
    echo "ERROR: no release to roll back to (target: '${TARGET:-}')" >&2
    exit 1
fi

ln -sfn "$RELEASES_DIR/$TARGET" "${CURRENT_LINK}.tmp"
mv -Tf "${CURRENT_LINK}.tmp" "$CURRENT_LINK"
echo "rolled back: current -> $TARGET (was $current_version)"
echo "activate with: systemctl --user restart idx-walkforward"
