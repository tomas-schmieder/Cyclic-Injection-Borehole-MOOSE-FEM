#!/usr/bin/env python3
"""
Post-process borehole1 cyclic-injection runs.

Reads the per-timestep LineValueSampler CSVs that MOOSE writes into
results/<case>/ and produces, in results/summary/:

  combined_<field>_<region>.csv   per case, under results/<case>/
  plot_<case>.png                 3D pore pressure and displacement surfaces
  comparison_pressure_t500.png    radial pressure profiles at t = 500 s
  comparison_displacement_t500.png
  permeability_summary.csv        max/avg pressure and displacement per case

Usage:
  scripts/postprocess.py                    # every case present in results/
  scripts/postprocess.py medium_sand low_silt
  scripts/postprocess.py --no-plots         # combine + summary only

This consolidates the logic that was spread across eight partly redundant cells
of the original analysis/cyclic.ipynb, with the hardcoded absolute paths
replaced by paths relative to the repository root.
"""

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "results")
SUMMARY = os.path.join(RESULTS, "summary")

REGIONS = ["left", "middle", "right"]
TARGET_TIME = 500.0

# Cases whose profiles go on the comparison figures, in legend order.
COMPARISON_CASES = [
    "anisotropic_x_high",
    "anisotropic_y_high",
    "y_blocked",
    "cross_coupled",
    "high_gravel",
    "medium_sand",
    "very_high_karst",
    "very_low_clay",
]

LABELS = {
    "anisotropic_x_high": "X High",
    "anisotropic_y_high": "Y High",
    "y_blocked": "Y Blocked",
    "cross_coupled": "Cross-Coupled",
    "high_gravel": "1e-10",
    "medium_sand": "1e-13",
    "very_high_karst": "1e-7",
    "very_low_clay": "1e-20",
    "extreme_1e-3": "1e-3",
    "low_silt": "1e-16",
    "base": "Base (cross-coupled 5e-14)",
}


def input_path(case):
    """Locate the input file that produced a results directory."""
    if case == "base":
        return os.path.join(REPO, "inputs", "cycle1_base.i")
    return os.path.join(REPO, "inputs", "cases", case + ".i")


def read_case_params(case):
    """Pull the permeability tensor and dt back out of the input file."""
    perm, dt = "N/A", 0.5
    path = input_path(case)
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                s = line.strip()
                if perm == "N/A" and s.startswith("permeability"):
                    perm = s.split("=", 1)[1].strip().strip("'")
                elif s.startswith("dt ="):
                    dt = float(s.split("=", 1)[1])
    return perm, dt


def load_field(case_dir, field, column, dt):
    """Concatenate every per-timestep CSV for one field into a tidy frame."""
    frames = []
    for region in REGIONS:
        parts = []
        step = 1
        while True:
            path = os.path.join(case_dir, f"output_{field}_{region}_{step:04d}.csv")
            if not os.path.exists(path):
                # MOOSE zero-pads to 4 digits, then widens; stop at the first gap
                # only after checking the wider form.
                wide = os.path.join(case_dir, f"output_{field}_{region}_{step:05d}.csv")
                if not os.path.exists(wide):
                    break
                path = wide
            df = pd.read_csv(path)
            df["timestep"] = step
            parts.append(df[["timestep", "x", column]])
            step += 1
        if parts:
            out = pd.concat(parts, ignore_index=True)
            out["time"] = out["timestep"] * dt
            out["region"] = region
            frames.append(out)
    return pd.concat(frames) if frames else None


def combine(case, case_dir, dt, write_csv=True):
    pressure = load_field(case_dir, "pressure", "porepressure", dt)
    disp = load_field(case_dir, "disp", "disp_y", dt)
    if pressure is None or disp is None:
        return None, None
    if write_csv:
        for region in REGIONS:
            pressure[pressure.region == region].to_csv(
                os.path.join(case_dir, f"combined_pressure_{region}.csv"), index=False
            )
            disp[disp.region == region].to_csv(
                os.path.join(case_dir, f"combined_disp_{region}.csv"), index=False
            )
    return pressure, disp


def plot_case(case, pressure, disp, perm, end_time):
    """3D pore-pressure and displacement surfaces, one figure per case."""
    fig = plt.figure(figsize=(20, 10))

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    for region in REGIONS:
        sub = pressure[pressure.region == region]
        ax1.plot_trisurf(sub["time"], sub["x"], sub["porepressure"],
                         cmap="viridis", linewidth=0.1, alpha=0.8)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Radius (m)")
    ax1.set_zlabel("Pore Pressure (Pa)", labelpad=-30)
    ax1.set_title(f"Pore Pressure vs. Radius vs. Time\nPermeability: {perm}")
    ax1.set_xlim(0, end_time)
    ax1.set_ylim(0, 50)
    ax1.view_init(elev=30, azim=130)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    for region in REGIONS:
        sub = disp[disp.region == region]
        ax2.plot_trisurf(sub["time"], sub["x"], sub["disp_y"],
                         cmap="plasma", linewidth=0.1, alpha=0.8)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Radius (m)")
    ax2.set_zlabel("Vertical Displacement (m)", labelpad=-30)
    ax2.set_title(f"Surface Displacement vs. Radius vs. Time\nPermeability: {perm}")
    ax2.set_xlim(0, end_time)
    ax2.set_ylim(0, 50)
    ax2.view_init(elev=30, azim=130)

    out = os.path.join(SUMMARY, f"plot_{case}.png")
    plt.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close(fig)
    return out


def profile_at(df, column, dt):
    """Radial profile at t = TARGET_TIME, averaged over regions.

    The original notebook dropped the first 10 samples per x-station to skip the
    initial transient before slicing; that is preserved here.
    """
    by_x = df.groupby("x")
    sizes = by_x["x"].transform("size")
    trimmed = df[(by_x.cumcount() >= 10) | (sizes <= 10)]
    sl = trimmed[np.abs(trimmed["time"] - TARGET_TIME) < dt / 2]
    if sl.empty:
        return None
    return sl.groupby("x")[column].mean().reset_index()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="*", help="cases to process (default: all in results/)")
    ap.add_argument("--no-plots", action="store_true", help="skip figure generation")
    args = ap.parse_args()

    os.makedirs(SUMMARY, exist_ok=True)

    if args.cases:
        cases = args.cases
    else:
        cases = sorted(d for d in os.listdir(RESULTS)
                       if d != "summary" and os.path.isdir(os.path.join(RESULTS, d)))
    if not cases:
        print(f"no case directories under {RESULTS} — run scripts/run_all.sh first",
              file=sys.stderr)
        return 1

    rows, p_profiles, d_profiles = [], [], []

    for case in cases:
        case_dir = os.path.join(RESULTS, case)
        if not os.path.isdir(case_dir):
            print(f"[skip] {case}: no results/{case}/", file=sys.stderr)
            continue

        perm, dt = read_case_params(case)
        pressure, disp = combine(case, case_dir, dt)
        if pressure is None:
            print(f"[skip] {case}: no sampler CSVs found", file=sys.stderr)
            continue

        end_time = pressure["time"].max()
        print(f"{case}: {len(pressure)} pressure samples, t up to {end_time:g} s, k = {perm}")

        rows.append({
            "case": case,
            "label": LABELS.get(case, case),
            "permeability": perm,
            "dt": dt,
            "end_time": end_time,
            "max_pressure_Pa": pressure["porepressure"].max(),
            "avg_pressure_Pa": pressure["porepressure"].mean(),
            "max_disp_y_m": disp["disp_y"].max(),
            "avg_disp_y_m": disp["disp_y"].mean(),
        })

        if not args.no_plots:
            print("  wrote", os.path.relpath(plot_case(case, pressure, disp, perm, end_time), REPO))

        if case in COMPARISON_CASES:
            p = profile_at(pressure, "porepressure", dt)
            d = profile_at(disp, "disp_y", dt)
            if p is not None and d is not None:
                p["case"], d["case"] = case, case
                p_profiles.append(p)
                d_profiles.append(d)

    if rows:
        summary_path = os.path.join(SUMMARY, "permeability_summary.csv")
        pd.DataFrame(rows).to_csv(summary_path, index=False)
        print("wrote", os.path.relpath(summary_path, REPO))

    if not args.no_plots and p_profiles:
        order = {c: i for i, c in enumerate(COMPARISON_CASES)}
        for profiles, column, ylabel, title, fname in [
            (p_profiles, "porepressure", "Pore Pressure (Pa)",
             f"Pore Pressure vs Radius at t = {TARGET_TIME:g} s", "comparison_pressure_t500.png"),
            (d_profiles, "disp_y", "Vertical Displacement (m)",
             f"Surface Displacement vs Radius at t = {TARGET_TIME:g} s",
             "comparison_displacement_t500.png"),
        ]:
            plt.figure(figsize=(10, 5))
            for df in sorted(profiles, key=lambda f: order.get(f["case"].iloc[0], 99)):
                case = df["case"].iloc[0]
                plt.plot(df["x"], df[column], label=LABELS.get(case, case))
            plt.xlabel("Radius (m)")
            plt.ylabel(ylabel)
            plt.title(title)
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            out = os.path.join(SUMMARY, fname)
            plt.savefig(out, dpi=300)
            plt.close()
            print("wrote", os.path.relpath(out, REPO))

    return 0


if __name__ == "__main__":
    sys.exit(main())
