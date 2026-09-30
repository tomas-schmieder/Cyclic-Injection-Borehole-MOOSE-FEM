#!/usr/bin/env python3
"""
Theory figures for the README:

  figures/regime_diagram.png     hydraulic-diffusion regime map (Deborah number vs k)
  figures/peak_pressure_vs_k.png peak pressure rise vs permeability, at the samplers
                                 and at the well walls, with an analytic reference
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


RW = 1.0                                             # well radius, m
Q0 = 1e4 * 315e-6 / (2.0 * np.pi * RW * 20.0)        # wall mass-flux amplitude, kg m^-2 s^-1
RHO = 1000.0                                         # fluid density, kg/m^3
R_SAMPLER = RW + 0.5                                 # nearest sampler: 0.5 m off each wall


def analytic_amplitude(k, r):
    """Pressure amplitude around one well with a sinusoidal wall flux, in Pa.

    Periodic steady state of p_t = c lap(p) in an infinite plane around a
    cylinder of radius RW carrying mass flux Q0 sin(wt) on its wall:
        p = Re{ A K0(lam r) e^{iwt} },  lam = sqrt(iw/c),
        A = Q0 mu / (rho k lam K1(lam RW)).
    Ignores the second well, the domain boundaries, the start-up transient and
    the mechanical coupling, so it is an order-of-magnitude reference, not a
    prediction of the coupled model. Needs scipy (Bessel functions of complex
    argument); returns None without it.
    """
    try:
        from scipy.special import kve
    except ImportError:
        return None
    k = np.asarray(k, dtype=float)
    lam = np.sqrt(1j * (2.0 * np.pi / T) / diffusivity(k))
    # Exponentially scaled Bessel functions, kve(n, z) = kv(n, z) e^z, so that
    # K0(lam r) / K1(lam RW) stays finite in tight rock where both underflow.
    ratio = kve(0, lam * r) / kve(1, lam * RW) * np.exp(-lam * (r - RW))
    return np.abs(Q0 * MU / (RHO * k * lam) * ratio)


def peak_pressure_vs_k():
    """Peak pressure rise vs k: at the nearest sampler, at the well wall, and analytic.

    The mid-depth samplers stop 0.5 m short of each well wall. The pressure the
    wells impose rises monotonically as k falls, but in tight rock it decays to
    nothing within that 0.5 m, so the sampler peak rises, tops out near
    k ~ 1e-15 to 1e-16 (silt), and collapses again. That is the "silt anomaly"
    of the original study. Archives from before the September 2026 revision
    have no well-wall data; the wall curve is then drawn from the analytic
    solution alone.
    """
    samp, wall = {}, {}
    with open(os.path.join(FIGS, "summary.csv")) as fh:
        for row in csv.DictReader(fh):
            samp[row["case"]] = float(row["max_pressure_Pa"])
            w = row.get("max_wall_pressure_Pa", "")
            if w not in ("", "nan"):
                wall[row["case"]] = float(w)
    case_k = {"high_gravel": 1e-10, "medium_sand": 1e-13, "low_silt": 1e-16,
              "very_low_clay": 1e-20, "very_high_karst": 1e-7, "extreme_1e-3": 1e-3}
    p0 = 1e6
    floor = 1e-9  # MPa; keeps rises of ~0 Pa visible on a log axis

    def rise(v):
        return max((v - p0) / 1e6, floor)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    # The analytic solution assumes an infinite medium, which holds while the
    # periodic diffusion length sqrt(c T / 2 pi) is shorter than the ~14 m from
    # each well to the fixed-pressure side walls: k up to ~1e-13 m^2. Above
    # that the side walls bleed pressure off and it overestimates by 2-5x.
    ks_a = np.logspace(-20.5, -12.5, 300)
    a_wall = analytic_amplitude(ks_a, RW)
    if a_wall is not None:
        a_samp = analytic_amplitude(ks_a, R_SAMPLER)
        ax.plot(ks_a, np.maximum(a_wall / 1e6, floor), color="#c0392b", lw=1.2, ls="--",
                label="analytic, at the well wall (single well, periodic)")
        ax.plot(ks_a, np.maximum(a_samp / 1e6, floor), color="#2c6fbb", lw=1.2, ls="--",
                label="analytic, 0.5 m from the wall (nearest sampler)")

    pts = sorted((k, c) for c, k in case_k.items() if c in samp)
    ax.plot([k for k, _ in pts], [rise(samp[c]) for _, c in pts], "o-", color="#2c6fbb",
            lw=1.8, ms=7, zorder=3, label="model, peak at the mid-depth samplers")
    wpts = [(k, c) for k, c in pts if c in wall]
    if wpts:
        ax.plot([k for k, _ in wpts], [rise(wall[c]) for _, c in wpts], "s-", color="#c0392b",
                lw=1.8, ms=7, zorder=3, label="model, peak on the well walls")
    for k, c in pts:
        ax.annotate(c.replace("_", " "), (k, rise(samp[c])), textcoords="offset points",
                    xytext=(6, -12), fontsize=8.5)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-21, 1e-2)
    ax.set_ylim(floor / 3, 1e5)
    ax.set_xlabel("isotropic permeability  $k$  (m$^2$)")
    ax.set_ylabel("peak pressure rise above 1 MPa  (MPa)")
    ax.set_title("Peak pressure vs permeability: where it is measured decides the trend")
    ax.grid(True, which="major", alpha=0.25)
    ax.legend(loc="upper right", fontsize=8.5)
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
