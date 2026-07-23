#!/bin/bash
# Run every permeability case in sequence.
#
#   scripts/run_all.sh              # all cases
#   scripts/run_all.sh low_silt y_blocked    # just these
#
# Each case is ~2000 timesteps and takes roughly 20-25 minutes on an M-series
# Mac, writing ~460 MB of Exodus output plus ~12,000 per-timestep CSVs into
# results/<case>/. Budget ~5 GB and ~4 hours for the full set; the
# very_low_clay_dt0.05 refinement run alone is 20,000 steps and ~4.5 GB.
#
# This replaces the original runall.sh, which hardcoded an absolute input
# directory and contained a typo ("cycle1_anisotropic_x_high.i"ch) that silently
# skipped the anisotropic_x_high case.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

if [ "$#" -gt 0 ]; then
  CASES=("$@")
else
  CASES=(base)
  while IFS= read -r c; do CASES+=("$c"); done < <(ls inputs/cases/*.i | xargs -n1 basename | sed 's/\.i$//')
fi

failed=()
for c in "${CASES[@]}"; do
  if ! scripts/run_case.sh "$c"; then
    echo "!!! $c FAILED" >&2
    failed+=("$c")
  fi
  echo "-----------------------------"
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "failed cases: ${failed[*]}" >&2
  exit 1
fi
echo "all cases completed"
