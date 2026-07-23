#!/bin/bash
# One-time setup: create the MOOSE environment with miniforge/mamba, then apply
# the macOS rpath workaround.
#
#   scripts/setup.sh
#
# Requires miniforge (https://github.com/conda-forge/miniforge). This project
# does not use Anaconda or Miniconda, and does not need them installed.
set -eo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINIFORGE_ROOT="${MINIFORGE_ROOT:-$HOME/miniforge}"
MOOSE_ENV="${MOOSE_ENV:-moose}"
MOOSE_VERSION="${MOOSE_VERSION:-2025.03.03}"

if [ ! -d "$MINIFORGE_ROOT" ]; then
  cat >&2 <<EOF
error: no miniforge at $MINIFORGE_ROOT

Install it first:
  curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-\$(uname)-\$(uname -m).sh"
  bash Miniforge3-\$(uname)-\$(uname -m).sh -b -p \$HOME/miniforge

Then re-run this script. Set MINIFORGE_ROOT if you installed it elsewhere.
EOF
  exit 1
fi

MAMBA="$MINIFORGE_ROOT/bin/mamba"
[ -x "$MAMBA" ] || MAMBA="$MINIFORGE_ROOT/bin/conda"
[ -x "$MAMBA" ] || { echo "error: neither mamba nor conda found under $MINIFORGE_ROOT/bin" >&2; exit 1; }
echo "using $MAMBA"

if [ -d "$MINIFORGE_ROOT/envs/$MOOSE_ENV" ]; then
  echo "environment '$MOOSE_ENV' already exists — skipping creation"
else
  echo "creating '$MOOSE_ENV' (moose-dev $MOOSE_VERSION + analysis packages)..."
  "$MAMBA" create -n "$MOOSE_ENV" -y \
    -c https://conda.software.inl.gov/public -c conda-forge \
    "moose-dev=$MOOSE_VERSION" \
    numpy pandas matplotlib netcdf4
fi

echo
echo "applying the macOS duplicate-LC_RPATH workaround..."
CONDA_PREFIX="$MINIFORGE_ROOT/envs/$MOOSE_ENV" "$REPO/scripts/fix_macos_rpaths.sh"

cat <<EOF

Setup complete. Next:

  git -C ../moose checkout a7c04635529b5e7deb1cc7c080894582cfdb5cff   # pin MOOSE
  source scripts/env.sh
  make -j8
  scripts/run.sh medium_sand
EOF
