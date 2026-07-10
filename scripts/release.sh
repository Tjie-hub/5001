#!/bin/bash
# Build an immutable, versioned release from git HEAD and atomically switch
# the `current` symlink (security hardening Phase 4). Prod never runs from a
# mutable working tree again.
#
#   RELEASES_DIR  (default ~/releases/idx-walkforward)   release store
#   CURRENT_LINK  (default ~/idx-walkforward-current)    symlink systemd runs
#   PROJECT_DIR   (default: repo containing this script) source checkout
#   SHARED_PATHS  space-separated mutable paths symlinked into each release
#                 (default: ".env venv logs walkforward.db flow.db
#                  idx_data.db .stockbit_token")
#
# The service is NOT restarted; the activation command is printed instead
# (operator decision).
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
RELEASES_DIR="${RELEASES_DIR:-$HOME/releases/idx-walkforward}"
CURRENT_LINK="${CURRENT_LINK:-$HOME/idx-walkforward-current}"
SHARED_PATHS="${SHARED_PATHS-.env venv logs walkforward.db flow.db idx_data.db .stockbit_token}"
# NOTE: data/ is a tracked code package (data/db.py) so it ships inside the
# release read-only; the production DB must therefore be reached via an
# absolute DB_PATH in .env (validate_config aborts startup otherwise).

cd "$PROJECT_DIR"
GIT_SHA=$(git rev-parse HEAD)
SHORT_SHA=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
VERSION="$(date +%Y%m%d-%H%M%S)-${SHORT_SHA}"
DEST="$RELEASES_DIR/$VERSION"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "WARNING: uncommitted tracked changes exist; the release is built from HEAD only." >&2
fi

if [ -e "$DEST" ]; then
    echo "ERROR: release $VERSION already exists" >&2
    exit 1
fi

mkdir -p "$DEST"
git archive HEAD | tar -x -C "$DEST"

cat > "$DEST/release.json" <<EOF
{
  "version": "$VERSION",
  "git_sha": "$GIT_SHA",
  "branch": "$BRANCH",
  "built_at": "$(date -Is)",
  "built_by": "$(whoami)@$(hostname)"
}
EOF

# shared mutable state lives outside the release and is symlinked in
for p in $SHARED_PATHS; do
    if [ -e "$PROJECT_DIR/$p" ] && [ ! -e "$DEST/$p" ]; then
        ln -s "$PROJECT_DIR/$p" "$DEST/$p"
    fi
done

# freeze the code (chmod -R ignores symlinks during recursion, so shared
# state stays writable)
chmod -R a-w "$DEST"

# atomic switch: build the link aside, then rename over
ln -sfn "$DEST" "${CURRENT_LINK}.tmp"
mv -Tf "${CURRENT_LINK}.tmp" "$CURRENT_LINK"

echo "released $VERSION"
echo "current -> $DEST"
echo "activate with: systemctl --user restart idx-walkforward"
