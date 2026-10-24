"""Reproduce all results: python experiments/run_all.py [--quick]"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from repmem import NoiseModel, logical_failure, per_cycle_rate, physical_rate

ROOT = Path(__file__).resolve().parents[1]


def run(d: int, nm: NoiseModel, rounds: int, shots: int, seeds: int, decoder: str = "viterbi"):
    """Mean and std (over seeds) of the logical per-cycle flip rate."""
    rates = [per_cycle_rate(logical_failure(d, nm, rounds, shots, np.random.default_rng(1000 + s), decoder), rounds)
             for s in range(seeds)]
    return float(np.mean(rates)), float(np.std(rates))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    q = ap.parse_args().quick
    shots, seeds, rounds = (300, 2, 6) if q else (5000, 4, 10)
    shots7 = 100 if q else 1500
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "figures").mkdir(exist_ok=True)
    t0 = time.time()
    rows = []

    def add(sweep, d, dec, nm, m, s):
        ph = physical_rate(nm)
        rows.append(dict(sweep=sweep, d=d, decoder=dec, cycle_us=nm.cycle_us, p_meas=nm.p_meas, p_gate=nm.p_gate,
                         eps_logical=m, eps_std=s, eps_physical=ph, ratio=m / ph, ratio_std=s / ph))

    cycles = [0.5, 1.0, 2.0, 4.0] if not q else [1.0, 4.0]
    pms = [0.005, 0.01, 0.02, 0.05, 0.1] if not q else [0.02, 0.1]
    for d in (3, 5):  # noise sweep
        for cyc in cycles:
            for pm in pms:
                nm = NoiseModel(cycle_us=cyc, p_meas=pm)
                add("noise", d, "viterbi", nm, *run(d, nm, rounds, shots, seeds))
    base = NoiseModel()
    for d in (3, 5, 7):  # ablation: decoder and distance
        for dec in ("viterbi", "final"):
            if d == 7 and dec == "final":
                continue
            add("ablation", d, dec, base, *run(d, base, rounds, shots7 if d == 7 else shots, seeds, dec))
    for pg in ([0.0, 0.003, 0.006, 0.012, 0.03, 0.06, 0.1] if not q else [0.003]):  # gate-error sweep
        nm = NoiseModel(p_gate=pg)
        for d in (3, 5):
            add("gate", d, "viterbi", nm, *run(d, nm, rounds, shots, seeds))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "results.csv", index=False)
    runtime = time.time() - t0
    with open(ROOT / "results" / "meta.json", "w") as f:
        json.dump(dict(quick=q, shots=shots, seeds=seeds, rounds=rounds, t1_us=50.0, runtime_s=runtime), f, indent=1)

    nz = df[df.sweep == "noise"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, d in zip(axs, (3, 5)):
        piv = nz[nz.d == d].pivot(index="cycle_us", columns="p_meas", values="ratio")
        im = ax.imshow(np.log10(piv.values + 1e-6), origin="lower", cmap="RdBu_r", vmin=-1.5, vmax=1.5, aspect="auto")
        ax.set_xticks(range(len(piv.columns)), [str(c) for c in piv.columns])
        ax.set_yticks(range(len(piv.index)), [str(c) for c in piv.index])
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                ax.text(j, i, f"{piv.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
        ax.set_title(f"d={d}")
        ax.set_xlabel("ancilla readout error $p_m$")
    axs[0].set_ylabel("cycle time (µs)")
    fig.colorbar(im, ax=axs, label="log10(logical / physical); <0 beats break-even")
    fig.savefig(ROOT / "figures" / "breakeven_map.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    ab = df[df.sweep == "ablation"]
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    for dec, g in ab.groupby("decoder"):
        ax.errorbar(g.d, g.eps_logical, g.eps_std, marker="o", capsize=3, label=dec)
    ax.axhline(physical_rate(base), ls="--", c="k", label="unencoded qubit")
    ax.set_yscale("log")
    ax.set_xlabel("code distance d")
    ax.set_ylabel("logical flip rate per cycle")
    ax.set_xticks([3, 5, 7])
    ax.legend()
    fig.savefig(ROOT / "figures" / "distance_decoder.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    gt = df[df.sweep == "gate"]
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    for d, g in gt.groupby("d"):
        ax.errorbar(g.p_gate, g.ratio, g.ratio_std, marker="o", capsize=3, label=f"d={d}")
    ax.axhline(1, ls="--", c="k")
    ax.set_yscale("log")
    ax.set_xlabel("gate-induced data flip per cycle")
    ax.set_ylabel("logical / physical rate")
    ax.legend()
    fig.savefig(ROOT / "figures" / "gate_sweep.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(df.round(5).to_string())
    print("runtime", runtime)


if __name__ == "__main__":
    main()
