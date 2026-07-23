#!/bin/bash
# Work around a conda-forge packaging bug that breaks the MOOSE environment on
# macOS 15 and newer.
#
# libgfortran.5.dylib and libquadmath.0.dylib (conda-forge libgfortran5 13.2.0)
# each declare "@loader_path" twice as an LC_RPATH. Older dyld tolerated this;
# current dyld treats a duplicate LC_RPATH as a hard error and refuses to load
# the library, so borehole1-opt dies at startup with:
#
#   dyld: Library not loaded: @rpath/libgfortran.5.dylib
#     Reason: ... (duplicate LC_RPATH '@loader_path')
#
# This script copies the offending libraries into .rpath-shim/, strips the
# duplicate rpath, and re-signs them. Nothing inside the conda environment is
# modified. scripts/env.sh puts .rpath-shim/ ahead of the environment on
# DYLD_LIBRARY_PATH.
#
# Run once after creating the conda environment. Re-run if you rebuild it.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${CONDA_PREFIX:-$HOME/miniforge/envs/moose}"
SHIM="$REPO/.rpath-shim"

if [ ! -d "$ENV_PREFIX/lib" ]; then
  echo "error: no lib/ under $ENV_PREFIX — activate the moose env or set CONDA_PREFIX" >&2
  exit 1
fi

mkdir -p "$SHIM"
patched=0

for lib in "$ENV_PREFIX"/lib/*.dylib; do
  [ -f "$lib" ] || continue
  dups=$(otool -l "$lib" 2>/dev/null | awk '/LC_RPATH/{f=1} f&&/path /{print $2; f=0}' | sort | uniq -d)
  [ -n "$dups" ] || continue

  name=$(basename "$lib")
  cp -f "$lib" "$SHIM/$name"
  chmod u+w "$SHIM/$name"
  while IFS= read -r rp; do
    [ -n "$rp" ] || continue
    install_name_tool -delete_rpath "$rp" "$SHIM/$name" 2>/dev/null || true
  done <<< "$dups"
  codesign --force -s - "$SHIM/$name" >/dev/null 2>&1 || true
  echo "patched $name (removed duplicate rpath: $(echo $dups | tr '\n' ' '))"
  patched=$((patched + 1))
done

if [ "$patched" -eq 0 ]; then
  echo "no libraries with duplicate LC_RPATH found — nothing to patch"
  rmdir "$SHIM" 2>/dev/null || true
else
  echo "$patched librar$([ $patched -eq 1 ] && echo y || echo ies) patched into $SHIM"
fi
