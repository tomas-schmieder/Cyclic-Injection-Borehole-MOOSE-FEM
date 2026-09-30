# Load mesh/doublet.msh through MOOSE and write it back out, to confirm that the
# fracture and well lines arrive as 1D element blocks (not sidesets) sharing
# nodes with the matrix:
#
#   ./borehole1-opt -i inputs/doublet_mesh_check.i --mesh-only
#
# Writes doublet_mesh_check_in.e next to this file. Expected blocks: matrix (1),
# fracture (2), injector (3), producer (4); sidesets bottom, top, left, right;
# nodesets inj_perfs, prod_perfs. This is a mesh check only; the physics input
# for the doublet is the next step.

[Mesh]
  [file]
    type = FileMeshGenerator
    file = '../mesh/doublet.msh'
  []
[]
