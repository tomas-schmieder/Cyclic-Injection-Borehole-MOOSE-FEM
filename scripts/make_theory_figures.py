#!/usr/bin/env python3
"""
Theory figures for the README:

  figures/regime_diagram.png     hydraulic-diffusion regime map (Deborah number vs k)
  figures/peak_pressure_vs_k.png measured peak pore pressure vs permeability
  figures/derived_properties.csv poroelastic constants derived from the inputs

These turn the dimensional analysis in the README into pictures and tie the
permeability sweep to the flow regime it lands in. Run after scripts/figures.sh
(needs figures/summary.csv).
"""

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(REPO, "figures")

# --- material / model constants, straight from inputs/cycle.i ---
E = 5.0e9        # Young's modulus, Pa
NU = 0.3         # Poisson ratio
PHI = 0.2        # porosity
KF = 2.1e9       # fluid bulk modulus, Pa
ALPHA = 1.0      # Biot coefficient
MU = 1.0e-3      # fluid viscosity, Pa s
L = 20.0         # well spacing, m (injection x=15 -> abstraction x=35)
T = 500.0        # forcing period, s

# --- derived poroelastic constants ---
K = E / (3.0 * (1.0 - 2.0 * NU))      # drained bulk modulus
G = E / (2.0 * (1.0 + NU))            # shear modulus
KV = K + 4.0 * G / 3.0               # constrained (oedometric / P-wave) modulus
INV_M = PHI / KF                      # 1/Biot modulus (alpha=1 => grains incompressible)
M = 1.0 / INV_M                       # Biot modulus
S = INV_M + ALPHA ** 2 / KV           # constrained storage coefficient, 1/Pa


def diffusivity(k):          # hydraulic diffusivity c = k / (mu S), m^2/s
    return k / (MU * S)


def deborah(k):              # De = tau_diffusion / T = L^2 / (c T)
    return L ** 2 / (diffusivity(k) * T)


ISO = [  # isotropic cases: label, k
    ("gravel\n$10^{-10}$", 1e-10),
    ("sand\n$10^{-13}$", 1e-13),
    ("silt\n$10^{-16}$", 1e-16),
    ("clay\n$10^{-20}$", 1e-20),
    ("karst\n$10^{-7}$", 1e-7),
    ("extreme\n$10^{-3}$", 1e-3),
]


def write_derived_csv():
    path = os.path.join(FIGS, "derived_properties.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["quantity", "symbol", "value", "units"])
        w.writerow(["drained bulk modulus", "K", f"{K:.4e}", "Pa"])
        w.writerow(["shear modulus", "G", f"{G:.4e}", "Pa"])
        w.writerow(["constrained modulus", "K_v", f"{KV:.4e}", "Pa"])
        w.writerow(["Biot modulus", "M", f"{M:.4e}", "Pa"])
        w.writerow(["storage coefficient", "S", f"{S:.4e}", "1/Pa"])
        for name, k in ISO:
            tag = name.split("\n")[0]
            w.writerow([f"hydraulic diffusivity ({tag})", "c", f"{diffusivity(k):.4e}", "m^2/s"])
            w.writerow([f"Deborah number ({tag})", "De", f"{deborah(k):.4e}", "-"])
    return path


def regime_diagram():
    ks = np.logspace(-21, -2, 400)
    de = deborah(ks)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.axhspan(1e-11, 1, color="#2e8b57", alpha=0.08)
    ax.axhspan(1, 1e12, color="#c0392b", alpha=0.07)
    ax.plot(ks, de, color="#333", lw=2, zorder=2)
    ax.axhline(1, color="#555", ls="--", lw=1.2)

    ax.text(3e-21, 3e-11, "equilibrated within a cycle\n(pressure ~ uniform)",
            color="#1c6b3c", fontsize=10, va="bottom")
    ax.text(3e-21, 3e10, "signal trapped near wells\n(large local gradients)",
            color="#8e2b21", fontsize=10, va="top")
    ax.text(1.3e-3, 1.4, "De = 1  (diffusion time = forcing period)",
            color="#555", fontsize=9, ha="right", va="bottom")

    for label, k in ISO:
        d = deborah(k)
        ax.scatter([k], [d], s=70, zorder=5, edgecolor="#111",
                   color="#2c6fbb" if d < 1 else "#c0392b")
        ax.annotate(label, (k, d), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8.5, fontweight="bold")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-21, 1e-2)
    ax.set_ylim(1e-11, 1e12)
    ax.set_xlabel("isotropic permeability  $k$  (m$^2$)")
    ax.set_ylabel(r"Deborah number  $\mathrm{De}=L^2/(c\,T)$")
    ax.set_title("Flow regime vs permeability: where each case lands")
    ax.grid(True, which="major", alpha=0.25)
    fig.tight_layout()
    out = os.path.join(FIGS, "regime_diagram.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def peak_pressure_vs_k():
    summ = {}
    with open(os.path.join(FIGS, "summary.csv")) as fh:
        for row in csv.DictReader(fh):
            summ[row["case"]] = float(row["max_pressure_Pa"])
    case_k = {"high_gravel": 1e-10, "medium_sand": 1e-13, "low_silt": 1e-16,
              "very_low_clay": 1e-20, "very_high_karst": 1e-7, "extreme_1e-3": 1e-3}
    pts = sorted(((k, summ[c], c) for c, k in case_k.items() if c in summ))
    ks = [p[0] for p in pts]
    ps = [p[1] / 1e6 for p in pts]

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.axhline(1.0, color="#888", ls=":", lw=1.2, label="boundary pressure (1 MPa)")
    ax.plot(ks, ps, "-o", color="#2c6fbb", lw=1.8, ms=7, zorder=3)
    for k, p, c in pts:
        ax.annotate(c.replace("_", " "), (k, p / 1e6), textcoords="offset points",
                    xytext=(6, 6), fontsize=8.5)
    # flag the silt anomaly noted by the original author
    ax.annotate("anomalous local buildup\n(flagged by original author)",
                (1e-16, summ["low_silt"] / 1e6), textcoords="offset points",
                xytext=(20, -35), fontsize=9, color="#c0392b",
                arrowprops=dict(arrowstyle="->", color="#c0392b"))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("isotropic permeability  $k$  (m$^2$)")
    ax.set_ylabel("peak pore pressure  (MPa)")
    ax.set_title("Measured peak pore pressure vs permeability (isotropic cases)")
    ax.grid(True, which="major", alpha=0.25)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    out = os.path.join(FIGS, "peak_pressure_vs_k.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(f"K={K:.4e}  G={G:.4e}  K_v={KV:.4e}  M={M:.4e}  S={S:.4e}")
    for name, k in ISO:
        print(f"  {name.split(chr(10))[0]:8s} k={k:.0e}  c={diffusivity(k):.3e} m^2/s  De={deborah(k):.3e}")
    print("wrote", os.path.relpath(write_derived_csv(), REPO))
    print("wrote", os.path.relpath(regime_diagram(), REPO))
    print("wrote", os.path.relpath(peak_pressure_vs_k(), REPO))
