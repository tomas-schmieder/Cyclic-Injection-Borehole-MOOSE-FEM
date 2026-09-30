#!/usr/bin/env python3
"""
Generate the presentation assets embedded in the README:

  figures/domain_schematic.png   annotated model setup (domain, wells, BCs, samplers)
  figures/mesh.png               the actual gmsh mesh, showing well refinement
  figures/forcing.png            the injection/abstraction cycle q(t)
  figures/preview/*.png          downsized copies of the 3D surface plots for embedding

Run after scripts/figures.sh. Not part of the analysis pipeline -- purely for docs.
"""

import glob
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(REPO, "figures")
PREVIEW = os.path.join(FIGS, "preview")

W, H = 50.0, 25.0
RW = 1.0
XI, XA, YC = 15.0, 35.0, 12.5


def parse_msh(path):
    """Minimal gmsh 2.2 reader: node coords and triangle connectivity."""
    nodes, tris = {}, []
    with open(path) as fh:
        lines = fh.read().splitlines()
    i = 0
    while i < len(lines):
        if lines[i] == "$Nodes":
            n = int(lines[i + 1])
            for j in range(n):
                p = lines[i + 2 + j].split()
                nodes[int(p[0])] = (float(p[1]), float(p[2]))
            i += 2 + n
        elif lines[i] == "$Elements":
            m = int(lines[i + 1])
            for j in range(m):
                p = lines[i + 2 + j].split()
                etype = int(p[1])
                if etype == 2:  # 3-node triangle
                    ntags = int(p[2])
                    conn = [int(x) for x in p[3 + ntags:3 + ntags + 3]]
                    tris.append(conn)
            i += 2 + m
        else:
            i += 1
    ids = sorted(nodes)
    index = {nid: k for k, nid in enumerate(ids)}
    xy = np.array([nodes[nid] for nid in ids])
    triangles = np.array([[index[a], index[b], index[c]] for a, b, c in tris])
    return xy[:, 0], xy[:, 1], triangles


def schematic():
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec="#222"))

    # sampled lines, each drawn as the three sampler windows: mid-depth
    # (pressure and displacement) and ground surface (uplift)
    for yline, col in [(YC, "#1f9e6e"), (H, "#8e44ad")]:
        for x0, x1 in [(0, 13.5), (16.5, 33.5), (36.5, 50)]:
            ax.plot([x0, x1], [yline, yline], color=col, lw=2.5, solid_capstyle="round",
                    zorder=3)
        ax.scatter(np.concatenate([np.linspace(a, b, 8) for a, b in
                                   [(0, 13.5), (16.5, 33.5), (36.5, 50)]]),
                   [yline] * 24, s=9, color=col, zorder=4)

    inj = Circle((XI, YC), RW, facecolor="#2c6fbb", edgecolor="#123", lw=1.5, zorder=5)
    absw = Circle((XA, YC), RW, facecolor="#c0392b", edgecolor="#123", lw=1.5, zorder=5)
    ax.add_patch(inj)
    ax.add_patch(absw)
    ax.annotate("injection\nwell", (XI, YC + RW), (XI, YC + 5.2), ha="center", va="bottom",
                fontsize=10, color="#2c6fbb", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#2c6fbb"))
    ax.annotate("abstraction\nwell", (XA, YC + RW), (XA, YC + 5.2), ha="center", va="bottom",
                fontsize=10, color="#c0392b", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#c0392b"))

    # boundary condition labels
    ax.text(-1.2, YC, "p = 1 MPa\n$u_x$ = 0", ha="right", va="center", fontsize=9, color="#444")
    ax.text(W + 1.2, YC, "p = 1 MPa\n$u_x$ = 0", ha="left", va="center", fontsize=9, color="#444")
    ax.text(W / 2, -1.6, "$u_y$ = 0", ha="center", va="top", fontsize=9, color="#444")
    ax.text(W / 2, YC - 3.4, "mid-depth samplers, y = 12.5 m (p, $u_y$)", ha="center",
            va="top", fontsize=9, color="#1f9e6e")
    ax.text(W / 2, H + 1.0, "ground-surface samplers, y = 25 m ($u_y$)", ha="center",
            va="bottom", fontsize=9, color="#8e44ad")
    ax.text(W / 2, YC + 1.6, "well walls: max / min / mean p", ha="center", va="bottom",
            fontsize=8.5, color="#555")

    ax.set_xlim(-7, W + 7)
    ax.set_ylim(-5, H + 6)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Poroelastic aquifer: 50 m × 25 m, paired wells on a 500 s cycle")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = os.path.join(FIGS, "domain_schematic.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def mesh_figure():
    x, y, tris = parse_msh(os.path.join(REPO, "mesh", "cycle1.msh"))
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.triplot(x, y, tris, color="#3a6ea5", lw=0.3)
    ax.add_patch(Circle((XI, YC), RW, facecolor="#2c6fbb", alpha=0.25, edgecolor="#2c6fbb"))
    ax.add_patch(Circle((XA, YC), RW, facecolor="#c0392b", alpha=0.25, edgecolor="#c0392b"))
    ax.set_xlim(-1, W + 1)
    ax.set_ylim(-1, H + 1)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"gmsh mesh — {len(x)} nodes, {len(tris)} triangles, refined to 0.25 m at the wells")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = os.path.join(FIGS, "mesh.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def forcing_figure():
    t = np.linspace(0, 1000, 2000)
    amp = 10000 * (315e-6 / (2 * np.pi * 1 * 20))
    q = amp * np.sin(2 * np.pi * t / 500)
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(t, q, color="#2c6fbb", lw=1.8, label="injection well")
    ax.plot(t, -q, color="#c0392b", lw=1.8, label="abstraction well")
    ax.axhline(0, color="#999", lw=0.8)
    for c in range(1, 2):
        ax.axvline(500 * c, color="#ccc", lw=0.8, ls="--")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("mass flux into rock\n(kg m$^{-2}$ s$^{-1}$)")
    ax.set_title("Well forcing: two 500 s cycles, wells in antiphase")
    ax.set_xlim(0, 1000)
    ax.legend(loc="upper right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = os.path.join(FIGS, "forcing.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def previews():
    os.makedirs(PREVIEW, exist_ok=True)
    made = []
    for src in sorted(glob.glob(os.path.join(FIGS, "*.png"))):
        name = os.path.basename(src)
        img = plt.imread(src)
        h, w = img.shape[:2]
        target_w = 1200
        if w <= target_w:
            made.append((name, "copied"))
            plt.imsave(os.path.join(PREVIEW, name), img)
            continue
        scale = target_w / w
        fig = plt.figure(figsize=(target_w / 100, h * scale / 100), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(img)
        ax.axis("off")
        fig.savefig(os.path.join(PREVIEW, name), dpi=100)
        plt.close(fig)
        made.append((name, "downsized"))
    return made


if __name__ == "__main__":
    print("wrote", os.path.relpath(schematic(), REPO))
    print("wrote", os.path.relpath(mesh_figure(), REPO))
    print("wrote", os.path.relpath(forcing_figure(), REPO))
    for name, how in previews():
        print(f"  preview {how}: {name}")
