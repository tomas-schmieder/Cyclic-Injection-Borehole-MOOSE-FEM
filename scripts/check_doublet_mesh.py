#!/usr/bin/env python3
"""
Validate mesh/doublet.msh the way libMesh will read it, and draw it.

  scripts/check_doublet_mesh.py mesh/doublet.msh
  scripts/check_doublet_mesh.py mesh/doublet.msh --figure figures/mesh_doublet.png

MOOSE PorousFlow's explicit-fracture method needs a conforming mixed-dimensional
mesh: every 1D fracture (or well) element must be an edge of the 2D matrix
mesh, sharing its two nodes, and the 1D elements must form their own blocks.
This script checks that, plus the libMesh-specific tagging, without needing a
MOOSE build:

  * $PhysicalNames: the fracture, injector and producer groups carry the
    "lower_dimensional_block" tag and parse to the right names the way
    libMesh's GmshIO parses them (whitespace-split, quotes stripped)
  * conformity: each 1D block element is an edge of some matrix triangle
  * perforations: one node where each fracture crosses each lateral, shared by
    fracture, well and matrix
  * boundaries: sideset elements lie on the outer rectangle
  * no duplicate nodes; triangle quality; element sizes at the fractures

Exits non-zero on any failure.
"""

import argparse
import os
import sys
from collections import Counter, defaultdict

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FT = 0.3048
S, DC, NC = 365 * FT, 25 * FT, 6          # must match mesh/doublet.geo
LX, EXT, LY = NC * DC, 30.0, 150.0
LC_FRAC = 0.25

BLOCKS_1D = {"fracture", "injector", "producer"}
SIDESETS = {"bottom", "top", "left", "right"}
NODESETS = {"inj_perfs", "prod_perfs"}


def read_msh22(path):
    """Minimal gmsh 2.2 ASCII reader. Returns names, nodes, and elements by type."""
    with open(path) as fh:
        lines = fh.read().splitlines()
    names, raw_names = {}, {}
    nodes = {}
    elems = defaultdict(list)          # etype -> [(phys_tag, (node ids...))]
    i = 0
    while i < len(lines):
        s = lines[i]
        if s == "$MeshFormat":
            if not lines[i + 1].startswith("2.2 0"):
                raise SystemExit(f"expected ASCII msh 2.2, got '{lines[i + 1]}'")
            i += 2
        elif s == "$PhysicalNames":
            n = int(lines[i + 1])
            for line in lines[i + 2:i + 2 + n]:
                # GmshIO: `s_stream >> phys_dim >> phys_id >> phys_name`, then quotes erased.
                tok = line.split()
                dim, pid, name = int(tok[0]), int(tok[1]), tok[2].replace('"', "")
                names[pid] = (dim, name)
                raw_names[pid] = line
            i += 2 + n
        elif s == "$Nodes":
            n = int(lines[i + 1])
            for line in lines[i + 2:i + 2 + n]:
                p = line.split()
                nodes[int(p[0])] = (float(p[1]), float(p[2]))
            i += 2 + n
        elif s == "$Elements":
            n = int(lines[i + 1])
            for line in lines[i + 2:i + 2 + n]:
                p = [int(v) for v in line.split()]
                etype, ntags = p[1], p[2]
                elems[etype].append((p[3], tuple(p[3 + ntags:])))
            i += 2 + n
        else:
            i += 1
    return names, raw_names, nodes, elems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("msh")
    ap.add_argument("--figure", help="write an overview + zoom figure here")
    args = ap.parse_args()

    names, raw_names, nodes, elems = read_msh22(args.msh)
    failures = []

    def check(ok, msg):
        print(("  ok    " if ok else "  FAIL  ") + msg)
        if not ok:
            failures.append(msg)

    by_name = {nm: pid for pid, (dim, nm) in names.items()}
    print(f"{args.msh}: {len(nodes)} nodes, "
          + ", ".join(f"{len(v)} type-{t}" for t, v in sorted(elems.items())))

    # --- tagging, as GmshIO reads it ---
    print("physical names")
    for nm in sorted(BLOCKS_1D):
        pid = by_name.get(nm)
        check(pid is not None and names[pid][0] == 1
              and "lower_dimensional_block" in raw_names[pid],
              f"'{nm}' is a 1D group tagged lower_dimensional_block")
    for nm in sorted(SIDESETS):
        pid = by_name.get(nm)
        check(pid is not None and names[pid][0] == 1
              and "lower_dimensional_block" not in raw_names[pid],
              f"'{nm}' is an untagged 1D group (becomes a sideset)")
    for nm in sorted(NODESETS):
        pid = by_name.get(nm)
        check(pid is not None and names[pid][0] == 0, f"'{nm}' is a 0D group (nodeset)")
    check(by_name.get("matrix") is not None and names[by_name["matrix"]][0] == 2,
          "'matrix' is the 2D block")
    ids_2d_1d = [pid for pid, (d, nm) in names.items() if nm in BLOCKS_1D or nm == "matrix"]
    check(len(ids_2d_1d) == len(set(ids_2d_1d)) == 4, "block IDs are distinct")

    # --- geometry basics ---
    xy = np.array(list(nodes.values()))
    ids = np.array(list(nodes.keys()))
    pos = {nid: k for k, nid in enumerate(ids)}
    rounded = Counter(map(tuple, np.round(xy, 9)))
    check(max(rounded.values()) == 1, "no duplicate node coordinates")
    check(np.allclose([xy[:, 0].min(), xy[:, 0].max(), xy[:, 1].min(), xy[:, 1].max()],
                      [0, LX, -LY, S + LY]), "domain is the expected rectangle")

    tris = [c for tag, c in elems.get(2, []) if tag == by_name["matrix"]]
    check(len(tris) == len(elems.get(2, [])), "every triangle is in the matrix block")
    edges = set()
    for a, b, c in tris:
        for u, v in ((a, b), (b, c), (c, a)):
            edges.add((min(u, v), max(u, v)))

    lines = defaultdict(list)
    for tag, (u, v) in elems.get(1, []):
        lines[names[tag][1]].append((u, v))

    # --- conformity of every 1D block ---
    print("conformity")
    for nm in sorted(BLOCKS_1D):
        segs = lines[nm]
        miss = [s for s in segs if (min(s), max(s)) not in edges]
        check(segs and not miss, f"{nm}: all {len(segs)} line elements are matrix edges"
              + (f" ({len(miss)} are not)" if miss else ""))

    def seg_xy(segs):
        return np.array([[nodes[u], nodes[v]] for u, v in segs])

    fr = seg_xy(lines["fracture"])
    check(np.allclose(fr[:, 0, 0], fr[:, 1, 0]), "fracture elements are all vertical")
    fx = np.unique(np.round(fr[:, 0, 0], 9))
    expect_fx = DC / 2 + DC * np.arange(NC)
    check(fx.size == NC and np.allclose(fx, expect_fx),
          f"{NC} fractures at x = " + ", ".join(f"{v:.2f}" for v in fx))
    for x0 in fx:
        on = fr[np.isclose(fr[:, 0, 0], x0)]
        ylo, yhi = on[:, :, 1].min(), on[:, :, 1].max()
        length = np.abs(on[:, 1, 1] - on[:, 0, 1]).sum()
        ok = np.isclose(ylo, -EXT) and np.isclose(yhi, S + EXT) and np.isclose(length, S + 2 * EXT)
        if not ok:
            check(False, f"fracture at x={x0:.2f} spans y {ylo:.2f}..{yhi:.2f}, length {length:.2f}")
    check(True, f"each fracture is one gap-free line from y = {-EXT:g} to {S + EXT:.2f}")
    flen = np.abs(fr[:, 1, 1] - fr[:, 0, 1])
    check(flen.max() <= 1.2 * LC_FRAC, f"fracture element length {flen.min():.3f}-{flen.max():.3f} m "
          f"(target {LC_FRAC} m)")

    for nm, y0 in (("injector", 0.0), ("producer", S)):
        w = seg_xy(lines[nm])
        ok = np.allclose(w[:, :, 1], y0) and np.isclose(np.abs(w[:, 1, 0] - w[:, 0, 0]).sum(), LX)
        check(ok, f"{nm} is a gap-free line at y = {y0:.2f}, x = 0..{LX:.2f}")

    # --- perforations ---
    print("perforations")
    frac_nodes = {n for s in lines["fracture"] for n in s}
    tri_nodes = {n for t in tris for n in t}
    for nm, well, y0 in (("inj_perfs", "injector", 0.0), ("prod_perfs", "producer", S)):
        pts = [c[0] for tag, c in elems.get(15, []) if tag == by_name[nm]]
        well_nodes = {n for s in lines[well] for n in s}
        pxy = np.array([nodes[n] for n in pts])
        ok = (len(pts) == NC and np.allclose(np.sort(pxy[:, 0]), expect_fx)
              and np.allclose(pxy[:, 1], y0)
              and all(n in frac_nodes and n in well_nodes and n in tri_nodes for n in pts))
        check(ok, f"{nm}: {len(pts)} nodes, each shared by fracture, {well} and matrix")

    # --- outer boundary ---
    print("boundaries")
    for nm, test in (("bottom", lambda p: np.isclose(p[:, 1], -LY)),
                     ("top", lambda p: np.isclose(p[:, 1], S + LY)),
                     ("left", lambda p: np.isclose(p[:, 0], 0)),
                     ("right", lambda p: np.isclose(p[:, 0], LX))):
        p = seg_xy(lines[nm]).reshape(-1, 2)
        miss = [s for s in lines[nm] if (min(s), max(s)) not in edges]
        check(len(p) and test(p).all() and not miss,
              f"{nm}: {len(lines[nm])} edges, all on the wall and all matrix edges")

    # --- triangle quality ---
    print("quality")
    T = np.array([[pos[a], pos[b], pos[c]] for a, b, c in tris])
    P = xy[T]
    e1, e2 = P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]
    area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    L = np.stack([np.linalg.norm(P[:, (k + 1) % 3] - P[:, k], axis=1) for k in range(3)], 1)
    angles = []
    for k in range(3):
        a, b, c = L[:, k], L[:, (k + 1) % 3], L[:, (k + 2) % 3]
        angles.append(np.degrees(np.arccos(np.clip((b ** 2 + c ** 2 - a ** 2) / (2 * b * c), -1, 1))))
    minang = np.min(angles, axis=0)
    check(area.min() > 0, f"all {len(tris)} triangles have positive area")
    check(minang.min() > 15, f"minimum angle {minang.min():.1f} deg "
          f"(1st percentile {np.percentile(minang, 1):.1f}, median {np.median(minang):.1f})")
    check(np.isclose(area.sum(), LX * (S + 2 * LY), rtol=1e-9),
          f"triangles tile the domain exactly ({area.sum():.2f} m^2)")

    if args.figure:
        draw(args.figure, xy, T, seg_xy(lines["fracture"]), seg_xy(lines["injector"]),
             seg_xy(lines["producer"]), len(nodes), len(tris))

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


def draw(out, xy, T, frac, inj, prod, n_nodes, n_tris):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 7.4), gridspec_kw={"width_ratios": [1, 1.25]})
    zoom = (0, LX, -12, 12)
    for ax, lw in ((ax1, 0.08), (ax2, 0.25)):
        ax.triplot(xy[:, 0], xy[:, 1], T, color="#8aa6c4", lw=lw)
        ax.add_collection(LineCollection(frac, colors="#d35400", lw=1.6, zorder=3))
        ax.add_collection(LineCollection(inj, colors="#2c6fbb", lw=2.4, zorder=4))
        ax.add_collection(LineCollection(prod, colors="#c0392b", lw=2.4, zorder=4))
        ax.set_aspect("equal")
        ax.set_xlabel("x, along the laterals (m)")
        ax.spines[["top", "right"]].set_visible(False)
    ax1.set_ylabel("y, across the laterals (m)")
    ax1.set_xlim(-2, LX + 2)
    ax1.set_ylim(-LY - 5, S + LY + 5)
    ax1.add_patch(Rectangle((zoom[0], zoom[2]), zoom[1] - zoom[0], zoom[3] - zoom[2],
                            fill=False, ec="#222", lw=1, ls="--", zorder=5))
    ax1.text(LX + 3, 0, "injector", color="#2c6fbb", va="center", fontsize=9, fontweight="bold")
    ax1.text(LX + 3, S, "producer", color="#c0392b", va="center", fontsize=9, fontweight="bold")
    ax1.set_title("one stage, plan view", fontsize=10)
    ax2.set_xlim(zoom[0], zoom[1])
    ax2.set_ylim(zoom[2], zoom[3])
    ax2.set_title("zoom: fractures crossing the injector", fontsize=10)
    fig.suptitle(f"Fractured horizontal doublet mesh: {n_nodes:,} nodes, {n_tris:,} triangles; "
                 f"6 fractures at 25 ft, laterals 365 ft apart", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())
