#!/bin/bash
# Shared environment setup for the borehole1 MOOSE app.
# Sourced by run_case.sh / run_all.sh; safe to source directly in a shell.

CONDA_ENV="${MOOSE_CONDA_ENV:-moose}"
CONDA_SH="${CONDA_SH:-$HOME/miniforge/etc/profile.d/conda.sh}"

if [ -f "$CONDA_SH" ]; then
  # conda's activate.d hooks reference unset variables (GFORTRAN et al.), so
  # relax nounset across activation for callers running under `set -u`.
  __nounset=$(set -o | awk '$1=="nounset"{print $2}')
  set +u
  # shellcheck disable=SC1090
  source "$CONDA_SH"
  conda activate "$CONDA_ENV"
  [ "$__nounset" = "on" ] && set -u
  unset __nounset
else
  echo "warning: $CONDA_SH not found; assuming the MOOSE environment is already active" >&2
fi

# macOS 15+ dyld rejects libraries carrying a duplicate LC_RPATH. The conda-forge
# libgfortran5 / libquadmath builds shipped with the MOOSE environment do exactly
# that, so the app fails to launch with:
#   Library not loaded: @rpath/libgfortran.5.dylib ... (duplicate LC_RPATH '@loader_path')
# scripts/fix_macos_rpaths.sh writes patched copies into .rpath-shim/; prepend it
# if it exists so the patched copies win.
SHIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.rpath-shim"
if [ -d "$SHIM" ]; then
  export DYLD_LIBRARY_PATH="$SHIM${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
fi
