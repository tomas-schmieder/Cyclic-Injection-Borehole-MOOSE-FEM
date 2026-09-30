#!/usr/bin/env python3
"""
Fold a case's per-timestep sampler CSVs into a single compressed .npz archive.

MOOSE writes one CSV per VectorPostprocessor per timestep: nine samplers over
2000 steps is 18,000 files and ~30 MB, and the Exodus field file on top of that
takes a full case to ~758 MB. Almost none of that is information -- the whole
study needs only pore pressure and vertical displacement as a function of x and
time. Reshaped into two dense arrays and compressed, one case is ~2.6 MB, a 293x
reduction with no data loss.

  scripts/archive.py medium_sand              # results/medium_sand/ -> data/medium_sand.npz
  scripts/archive.py medium_sand --keep-raw   # keep the CSVs afterwards
  scripts/archive.py medium_sand --stride 10  # keep every 10th timestep

Archive contents (float64 throughout -- float32 is half the size but cannot
resolve the ~1e-7 Pa differences that distinguish the high-permeability cases):

  pressure_vals   (n_steps, n_x)  pore pressure at mid-depth (y = 12.5 m), Pa
  disp_vals       (n_steps, n_x)  vertical displacement at mid-depth, m
  surface_vals    (n_steps, n_x)  vertical displacement at the ground surface (y = 25 m), m
  wells           (n_steps, 6)    well-wall pore pressure, Pa; columns in well_cols
  well_cols       (6,)            inj/abs x max/min/avg postprocessor names
  steps           (n_steps,)      timestep index
  time            (n_steps,)      simulation time, s
  x               (n_x,)          sample position, m
  meta            json blob: case name, permeability, dt, source file count

The three sampler windows are merged on the x axis; x is the key, not the
region name (the original study's names were inconsistent between fields --
see docs/CORRECTIONS.md, item 6).
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = {"pressure": "porepressure", "disp": "disp_y", "surface": "disp_y"}
WELL_COLS = ["inj_wall_p_max", "inj_wall_p_min", "inj_wall_p_avg",
             "abs_wall_p_max", "abs_wall_p_min", "abs_wall_p_avg"]
_STEP_RX = re.compile(r"_(\d+)\.csv$")


def case_params(case):
    """Recover the case's permeability and dt from cases.csv."""
    path = os.path.join(REPO, "cases.csv")
    if os.path.exists(path):
        import csv
        with open(path) as fh:
            for row in csv.DictReader(fh):
                if row["case"] == case:
                    return row.get("permeability", ""), float(row.get("dt", 0.5))
    return "", 0.5


def load_field(case_dir, kind, column, stride):
    """Merge the three regional samplers for one field into (steps, x, values)."""
    per_step = {}
    n_files = 0
    for path in glob.glob(os.path.join(case_dir, f"output_{kind}_*_[0-9]*.csv")):
        m = _STEP_RX.search(path)
        if not m:
            continue
        step = int(m.group(1))
        n_files += 1
        if stride > 1 and step % stride:
            continue
        df = pd.read_csv(path)
        if column not in df.columns:
            raise SystemExit(f"{path}: expected column '{column}', found {list(df.columns)}")
        per_step.setdefault(step, {}).update(
            zip(df["x"].to_numpy(dtype=float), df[column].to_numpy(dtype=float))
        )

    if not per_step:
        return None, None, None, n_files

    steps = np.array(sorted(per_step), dtype=np.int64)
    xs = np.array(sorted({x for row in per_step.values() for x in row}), dtype=np.float64)
    index = {x: i for i, x in enumerate(xs)}
    vals = np.full((steps.size, xs.size), np.nan, dtype=np.float64)
    for i, step in enumerate(steps):
        for x, v in per_step[step].items():
            vals[i, index[x]] = v
    return steps, xs, vals, n_files


def load_wells(case_dir, times):
    """Well-wall postprocessors from the scalar CSV (output.csv), one row per time.

    Rows are matched to the sampler timesteps by simulation time rather than by
    position, so an extra t = 0 row or a strided archive cannot misalign them.
    """
    path = os.path.join(case_dir, "output.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path}: missing -- the well-wall postprocessors were not written")
    df = pd.read_csv(path)
    missing = [c for c in WELL_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"{path}: missing columns {missing}")
    t = df["time"].to_numpy(dtype=np.float64)
    idx = np.clip(np.searchsorted(t, times), 0, t.size - 1)
    lower = np.clip(idx - 1, 0, t.size - 1)
    idx = np.where(np.abs(t[lower] - times) < np.abs(t[idx] - times), lower, idx)
    worst = float(np.max(np.abs(t[idx] - times)))
    if worst > 1e-6 * max(1.0, float(times.max())):
        raise SystemExit(f"{path}: no scalar row within tolerance of every sampled time "
                         f"(worst mismatch {worst:g} s) -- incomplete run?")
    return df[WELL_COLS].to_numpy(dtype=np.float64)[idx]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case")
    ap.add_argument("--stride", type=int, default=1,
                    help="keep every Nth timestep (default 1 = all)")
    ap.add_argument("--keep-raw", action="store_true",
                    help="do not delete the per-timestep CSVs afterwards")
    ap.add_argument("--results", default=None, help="override the results directory")
    args = ap.parse_args()

    case_dir = args.results or os.path.join(REPO, "results", args.case)
    if not os.path.isdir(case_dir):
        raise SystemExit(f"no such results directory: {case_dir}")

    perm, dt = case_params(args.case)
    out = {}
    meta = {"case": args.case, "permeability": perm, "dt": dt, "stride": args.stride}
    ref_steps = None
    total_files = 0

    for kind, column in FIELDS.items():
        steps, xs, vals, n_files = load_field(case_dir, kind, column, args.stride)
        total_files += n_files
        if steps is None:
            raise SystemExit(f"{args.case}: no '{kind}' sampler CSVs under {case_dir}")
        if ref_steps is None:
            ref_steps, ref_x = steps, xs
        elif not np.array_equal(steps, ref_steps):
            raise SystemExit(f"{args.case}: '{kind}' has {steps.size} steps, "
                             f"expected {ref_steps.size} — incomplete run?")
        elif not np.array_equal(xs, ref_x):
            raise SystemExit(f"{args.case}: '{kind}' x-grid differs from the pressure grid")
        out[f"{kind}_vals"] = vals
        n_nan = int(np.isnan(vals).sum())
        if n_nan:
            print(f"  warning: {kind} has {n_nan} missing samples", file=sys.stderr)

    out["steps"] = ref_steps
    out["time"] = ref_steps.astype(np.float64) * dt
    out["wells"] = load_wells(case_dir, out["time"])
    out["well_cols"] = np.array(WELL_COLS)
    out["x"] = ref_x
    meta["n_steps"] = int(ref_steps.size)
    meta["n_x"] = int(ref_x.size)
    meta["source_csv_files"] = total_files
    out["meta"] = np.array(json.dumps(meta))

    raw_files = glob.glob(os.path.join(case_dir, "output_*_[0-9]*.csv"))
    raw_files.append(os.path.join(case_dir, "output.csv"))
    raw_bytes = sum(os.path.getsize(f) for f in raw_files)

    data_dir = os.path.join(REPO, "data")
    os.makedirs(data_dir, exist_ok=True)
    dest = os.path.join(data_dir, f"{args.case}.npz")
    np.savez_compressed(dest, **out)
    new_bytes = os.path.getsize(dest)

    print(f"  {args.case}: {meta['n_steps']} steps x {meta['n_x']} x-points  ->  "
          f"data/{args.case}.npz  {new_bytes/1e6:.2f} MB "
          f"(from {total_files:,} CSVs / {raw_bytes/1e6:.1f} MB, "
          f"{raw_bytes/max(new_bytes,1):.0f}x smaller)")

    if not args.keep_raw:
        removed = 0
        for f in raw_files:
            os.remove(f)
            removed += 1
        for cp in glob.glob(os.path.join(case_dir, "*_cp")):
            if os.path.isdir(cp):
                shutil.rmtree(cp)
        print(f"  {args.case}: removed {removed:,} raw CSVs "
              f"(kept the archive; re-create them by re-running the case)")


if __name__ == "__main__":
    main()
