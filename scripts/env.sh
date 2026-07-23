#!/bin/bash
# Activate the miniforge environment that holds MOOSE, and put the rpath shim in
# front of it. Sourced by every other script; safe to source directly in a shell.
#
# Override the location or name if yours differ:
#   MINIFORGE_ROOT=/opt/miniforge MOOSE_ENV=moose-2025 source scripts/env.sh

MINIFORGE_ROOT="${MINIFORGE_ROOT:-$HOME/miniforge}"
MOOSE_ENV="${MOOSE_ENV:-moose}"

# Locate the repository root without relying on BASH_SOURCE, which does not
# exist in zsh -- this file is meant to be source-able from an interactive shell
# as well as from the bash scripts. Walk up from $PWD looking for cases.csv.
if [ -z "${MOOSE_REPO:-}" ]; then
  _d="$PWD"
  while [ "$_d" != "/" ] && [ ! -f "$_d/cases.csv" ]; do _d="$(dirname "$_d")"; done
  if [ -f "$_d/cases.csv" ]; then
    MOOSE_REPO="$_d"
  else
    echo "error: run this from inside the repository, or set MOOSE_REPO" >&2
    return 1 2>/dev/null || exit 1
  fi
fi
export MOOSE_REPO

if [ ! -d "$MINIFORGE_ROOT" ]; then
  echo "error: no miniforge at $MINIFORGE_ROOT" >&2
  echo "       install it from https://github.com/conda-forge/miniforge, or set MINIFORGE_ROOT" >&2
  return 1 2>/dev/null || exit 1
fi

# miniforge ships its shell hook under this name; mamba uses the same one.
HOOK="$MINIFORGE_ROOT/etc/profile.d/conda.sh"
if [ -f "$HOOK" ]; then
  # miniforge's activate.d hooks reference unset variables (GFORTRAN et al.), so
  # relax nounset across activation for callers running under `set -u`.
  __nounset=$(set -o | awk '$1=="nounset"{print $2}')
  set +u
  # shellcheck disable=SC1090
  source "$HOOK"
  conda activate "$MOOSE_ENV" 2>/dev/null || {
    echo "error: could not activate '$MOOSE_ENV' -- run scripts/setup.sh first" >&2
    [ "$__nounset" = "on" ] && set -u
    return 1 2>/dev/null || exit 1
  }
  [ "$__nounset" = "on" ] && set -u
  unset __nounset
else
  echo "warning: $HOOK not found; assuming the MOOSE environment is already active" >&2
fi

# macOS 15+ dyld rejects libraries carrying a duplicate LC_RPATH. The
# conda-forge libgfortran5 / libquadmath builds in the MOOSE environment do
# exactly that, which stops both borehole1-opt and `import numpy` from loading.
# scripts/fix_macos_rpaths.sh writes patched copies into .rpath-shim/.
SHIM="$MOOSE_REPO/.rpath-shim"
if [ -d "$SHIM" ]; then
  export DYLD_LIBRARY_PATH="$SHIM${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
fi

# Interpreter to use for the Python tooling. Called by path, never through
# /usr/bin/env: env is SIP-protected and macOS strips DYLD_* when exec'ing it,
# which would silently discard the shim above.
export MOOSE_PYTHON="${CONDA_PREFIX:-$MINIFORGE_ROOT/envs/$MOOSE_ENV}/bin/python"
