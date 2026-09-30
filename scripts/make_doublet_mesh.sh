#!/bin/bash
# Build mesh/doublet.msh from mesh/doublet.geo, tag its 1D blocks for libMesh,
# validate it, and draw figures/mesh_doublet.png.
#
#   scripts/make_doublet_mesh.sh
#
# gmsh writes 1D physical groups as ordinary $PhysicalNames entries, which
# libMesh would turn into sidesets. Appending "lower_dimensional_block" after
# the quoted name (the form libMesh's own tests/meshes/block.msh uses) makes
# libMesh keep the fracture, injector and producer lines as element blocks that
# share nodes with the matrix triangles.
set -eo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
# shellcheck disable=SC1091
source "$REPO/scripts/env.sh"

GMSH="${GMSH:-gmsh}"
command -v "$GMSH" >/dev/null || { echo "error: gmsh not found (conda install -c conda-forge gmsh=4.13.1)" >&2; exit 1; }

"$GMSH" mesh/doublet.geo -0 -o mesh/doublet.msh > /dev/null
sed -i.bak -E 's/^(1 [0-9]+ "(fracture|injector|producer)")$/\1 lower_dimensional_block/' mesh/doublet.msh
rm -f mesh/doublet.msh.bak

"$MOOSE_PYTHON" scripts/check_doublet_mesh.py mesh/doublet.msh --figure figures/mesh_doublet.png
