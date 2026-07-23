#!/bin/bash
# Build all figures from the committed data/*.npz archives. No simulation needed.
#
#   scripts/figures.sh
#   scripts/figures.sh medium_sand
#   scripts/figures.sh --table-only
#
# Goes through scripts/env.sh and calls the interpreter by path: /usr/bin/env is
# SIP-protected, so a "#!/usr/bin/env python3" shebang would lose DYLD_* and the
# rpath shim with it, and numpy would fail to import.
set -eo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$REPO/scripts/env.sh"

exec "$MOOSE_PYTHON" -u "$REPO/scripts/figures.py" "$@"
