#!/bin/sh
# Copies the repo's hooks into .git/hooks. Run once per machine — .git/hooks is not version
# controlled, so cloning the repo does NOT bring the hook with it.
set -e
root=$(git rev-parse --show-toplevel)
cp "$root/tools/pre-commit" "$root/.git/hooks/pre-commit"
chmod +x "$root/.git/hooks/pre-commit"
echo "pre-commit hook installed at .git/hooks/pre-commit"
