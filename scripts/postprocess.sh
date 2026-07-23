#!/bin/bash
# Wrapper around postprocess.py that guarantees the rpath shim is in effect.
#
#   scripts/postprocess.sh                 # all cases in results/
#   scripts/postprocess.sh medium_sand
#
# The shim has to be applied via DYLD_LIBRARY_PATH, and macOS strips DYLD_* when
# it execs a SIP-protected binary. /usr/bin/env is protected, so a
# "#!/usr/bin/env python3" shebang would lose the variable and numpy would fail
# to import with the same duplicate-LC_RPATH error the solver hits. Calling the
# conda interpreter by path avoids that.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$REPO/scripts/env.sh"

PY="${CONDA_PREFIX:-$HOME/miniforge/envs/moose}/bin/python"
if [ ! -x "$PY" ]; then
  echo "error: no python at $PY" >&2
  exit 1
fi

# -u so progress lines appear as cases finish rather than at the end when stdout
# is redirected to a file.
exec "$PY" -u "$REPO/scripts/postprocess.py" "$@"
