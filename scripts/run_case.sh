#!/bin/bash
# Run a single permeability case.
#
#   scripts/run_case.sh medium_sand
#   scripts/run_case.sh base            # the cross-coupled base case
#
# Output lands in results/<case>/ (each input sets its own file_base).
# Must be run from the repository root, which is where file_base is resolved.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

CASE="${1:-}"
if [ -z "$CASE" ]; then
  echo "usage: scripts/run_case.sh <case>" >&2
  echo "cases: base $(ls inputs/cases/*.i | xargs -n1 basename | sed 's/\.i$//' | tr '\n' ' ')" >&2
  exit 1
fi

if [ "$CASE" = "base" ]; then
  INPUT="inputs/cycle1_base.i"
else
  INPUT="inputs/cases/$CASE.i"
fi

if [ ! -f "$INPUT" ]; then
  echo "error: no such input: $INPUT" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$REPO/scripts/env.sh"

if [ ! -x "$REPO/borehole1-opt" ]; then
  echo "error: borehole1-opt not built — run 'make -j8' first" >&2
  exit 1
fi

NPROC="${NPROC:-1}"
echo "=== $CASE : $INPUT ($(date '+%H:%M:%S')) ==="
if [ "$NPROC" -gt 1 ]; then
  mpiexec -n "$NPROC" ./borehole1-opt -i "$INPUT"
else
  ./borehole1-opt -i "$INPUT"
fi
echo "=== $CASE done ($(date '+%H:%M:%S')) ==="
