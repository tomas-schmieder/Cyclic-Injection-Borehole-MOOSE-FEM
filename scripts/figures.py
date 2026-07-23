#!/usr/bin/env python3
"""
Build every figure and the summary table from the committed data/*.npz archives.

This needs no simulation: the archives are in the repository, so a fresh clone
can reproduce all of the study's figures in about a minute.

  scripts/figures.sh                  # every archive in data/
  scripts/figures.sh medium_sand      # just one
  scripts/figures.sh --table-only     # summary table, no plots

Outputs into figures/:
  plot_<case>.png                    3D pore pressure and displacement surfaces
  comparison_pressure_t500.png       radial pressure profiles at t = 500 s
  comparison_displacement_t500.png
  summary.csv                        max/mean pressure and displacement per case
"""

import argparse
import glob
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
FIGS = os.path.join(REPO, "figures")

TARGET_TIME = 500.0
DPI = 150  # 300 dpi produced ~6 MB per figure for no visible benefit

# Cases drawn on the comparison figures, in legend order.
COMPARISON = ["anisotropic_x_high", "anisotropic_y_high", "y_blocked", "cross_coupled",
              "high_gravel", "medium_sand", "very_high_karst", "very_low_clay"]


def load(case):
    path = os.path.join(DATA, f"{case}.npz")
    if not os.path.exists(path):
        return None
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    return {"case": case, "meta": meta, "time": z["time"], "x": z["x"],
            "pressure": z["pressure_vals"], "disp": z["disp_vals"]}


def label_for(d):
    """Prefer the human label from cases.csv, fall back to the case name."""
    path = os.path.join(REPO, "cases.csv")
    if os.path.exists(path):
        import csv
        with open(path) as fh:
            for row in csv.DictReader(fh):
                if row["case"] == d["case"]:
                    return row.get("label") or d["case"]
    return d["case"]


MAX_SURFACE_ROWS = 2000  # decimate for rendering only; statistics use every step


def plot_case(d):
    """3D surfaces over (time, radius) for both fields.

    The dt-refinement case has 20,000 timesteps; rendering all of them is slow
    and indistinguishable from a decimated surface, so the plot is thinned to at
    most MAX_SURFACE_ROWS rows. The summary statistics are always computed from
    the full array, never from this decimated view.
    """
    step = max(1, len(d["time"]) // MAX_SURFACE_ROWS)
    t, pressure, disp = d["time"][::step], d["pressure"][::step], d["disp"][::step]
    T, X = np.meshgrid(t, d["x"], indexing="ij")
    d = {**d, "pressure": pressure, "disp": disp}
    perm = d["meta"].get("permeability", "")
    end_time = float(t.max())

    fig = plt.figure(figsize=(20, 10))
    for idx, (key, cmap, zlabel, title) in enumerate([
        ("pressure", "viridis", "Pore Pressure (Pa)", "Pore Pressure vs. Radius vs. Time"),
        ("disp", "plasma", "Vertical Displacement (m)",
         "Surface Displacement vs. Radius vs. Time"),
    ]):
        ax = fig.add_subplot(1, 2, idx + 1, projection="3d")
        ax.plot_surface(T, X, d[key], cmap=cmap, linewidth=0, antialiased=True, alpha=0.9)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Radius (m)")
        ax.set_zlabel(zlabel, labelpad=-30)
        ax.set_title(f"{title}\nPermeability: {perm}")
        ax.set_xlim(0, end_time)
        ax.set_ylim(0, 50)
        ax.view_init(elev=30, azim=130)

    out = os.path.join(FIGS, f"plot_{d['case']}.png")
    plt.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return out


def profile_at(d, key):
    """Radial profile at t = TARGET_TIME, nearest available sample."""
    i = int(np.argmin(np.abs(d["time"] - TARGET_TIME)))
    if abs(d["time"][i] - TARGET_TIME) > d["meta"].get("dt", 0.5) * d["meta"].get("stride", 1):
        return None
    return d[key][i]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--table-only", action="store_true")
    args = ap.parse_args()

    os.makedirs(FIGS, exist_ok=True)
    cases = args.cases or sorted(
        os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(DATA, "*.npz")))
    if not cases:
        print(f"no archives in {DATA} — run scripts/run.sh first", file=sys.stderr)
        return 1

    rows, loaded = [], {}
    for case in cases:
        d = load(case)
        if d is None:
            print(f"[skip] {case}: no data/{case}.npz", file=sys.stderr)
            continue
        loaded[case] = d
        rows.append({
            "case": case,
            "label": label_for(d),
            "permeability": d["meta"].get("permeability", ""),
            "dt": d["meta"].get("dt"),
            "n_steps": d["meta"].get("n_steps"),
            "end_time_s": float(d["time"].max()),
            "max_pressure_Pa": float(np.nanmax(d["pressure"])),
            "mean_pressure_Pa": float(np.nanmean(d["pressure"])),
            "max_disp_y_m": float(np.nanmax(d["disp"])),
            "mean_disp_y_m": float(np.nanmean(d["disp"])),
        })
        print(f"{case}: {d['meta']['n_steps']} steps x {d['meta']['n_x']} x-points")
        if not args.table_only:
            print("  wrote", os.path.relpath(plot_case(d), REPO))

    if rows:
        path = os.path.join(FIGS, "summary.csv")
        pd.DataFrame(rows).to_csv(path, index=False)
        print("wrote", os.path.relpath(path, REPO))

    if args.table_only:
        return 0

    order = {c: i for i, c in enumerate(COMPARISON)}
    for key, ylabel, title, fname in [
        ("pressure", "Pore Pressure (Pa)",
         f"Pore Pressure vs Radius at t = {TARGET_TIME:g} s", "comparison_pressure_t500.png"),
        ("disp", "Vertical Displacement (m)",
         f"Surface Displacement vs Radius at t = {TARGET_TIME:g} s",
         "comparison_displacement_t500.png"),
    ]:
        drawn = 0
        plt.figure(figsize=(10, 5))
        for case in sorted(loaded, key=lambda c: order.get(c, 99)):
            if case not in order:
                continue
            prof = profile_at(loaded[case], key)
            if prof is None:
                print(f"  [skip] {case}: no sample near t={TARGET_TIME:g}s", file=sys.stderr)
                continue
            plt.plot(loaded[case]["x"], prof, label=label_for(loaded[case]))
            drawn += 1
        if not drawn:
            plt.close()
            continue
        plt.xlabel("Radius (m)")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        out = os.path.join(FIGS, fname)
        plt.savefig(out, dpi=DPI)
        plt.close()
        print("wrote", os.path.relpath(out, REPO), f"({drawn} cases)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
