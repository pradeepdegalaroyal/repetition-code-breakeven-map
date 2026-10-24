"""Phenomenological Monte Carlo of a distance-d bit-flip repetition-code memory.

Noise per QEC cycle: Pauli-twirled T1 idling over the cycle time, a gate-induced data flip,
and a classical flip of every ancilla readout. The final round is an ideal readout.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NoiseModel:
    """Noise parameters. Times in microseconds."""

    t1_us: float = 50.0
    cycle_us: float = 1.0
    p_gate: float = 0.003  # extra data bit-flip per cycle from syndrome-extraction CNOTs
    p_meas: float = 0.02  # ancilla readout flip probability

    @property
    def p_idle(self) -> float:
        """Twirled amplitude-damping bit-flip probability, averaged over |0>,|1>."""
        return float((1.0 - np.exp(-self.cycle_us / self.t1_us)) / 2.0)

    @property
    def p_data(self) -> float:
        """Total data-qubit flip probability per cycle (independent combination)."""
        return self.p_idle + self.p_gate - 2 * self.p_idle * self.p_gate


def physical_rate(nm: NoiseModel) -> float:
    """Per-cycle flip rate of one unencoded qubit idling for the same cycle time."""
    return nm.p_idle


def per_cycle_rate(fail: float, rounds: int) -> float:
    """Convert a failure probability after `rounds` cycles to an effective per-cycle flip rate."""
    f = min(fail, 0.499)
    return float((1.0 - (1.0 - 2.0 * f) ** (1.0 / rounds)) / 2.0)


def _tables(d: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    states = np.arange(2**d)
    bits = (states[:, None] >> np.arange(d)) & 1
    syn = bits[:, :-1] ^ bits[:, 1:]
    return states, bits.sum(1), syn


def logical_failure(d: int, nm: NoiseModel, rounds: int, shots: int, rng: np.random.Generator,
                    decoder: str = "viterbi") -> float:
    """Logical failure probability after `rounds` cycles.

    decoder: 'viterbi' = exact minimum-weight space-time decoding of the syndrome history;
             'final' = decode only the ideal last syndrome (no use of the history).
    """
    states, pc, synt = _tables(d)
    S = 2**d
    c = np.zeros(shots, dtype=np.int64)
    obs = []
    for _ in range(rounds):
        flips = (rng.random((shots, d)) < nm.p_data).astype(np.int64)
        c ^= flips @ (1 << np.arange(d))
        bits = (c[:, None] >> np.arange(d)) & 1
        syn = bits[:, :-1] ^ bits[:, 1:]
        m = (rng.random(syn.shape) < nm.p_meas).astype(np.int64)
        obs.append(syn ^ m)
    bits = (c[:, None] >> np.arange(d)) & 1
    final_syn = bits[:, :-1] ^ bits[:, 1:]
    if decoder == "final":
        return float(np.mean(pc[c] > d / 2))
    wd = np.log((1 - nm.p_data) / nm.p_data)
    wm = np.log((1 - nm.p_meas) / nm.p_meas)
    cost = np.full((shots, S), 1e9)
    cost[:, 0] = 0.0
    for o in obs:
        new = np.full((shots, S), np.inf)
        for e in range(S):
            new = np.minimum(new, cost[:, states ^ e] + wd * pc[e])
        mism = (o[:, None, :] != synt[None, :, :]).sum(2)
        cost = new + wm * mism
    ok = (final_syn[:, None, :] == synt[None, :, :]).all(2)
    cost = np.where(ok, cost, np.inf)
    est = np.argmin(cost, axis=1)
    return float(np.mean((c ^ est) == (S - 1)))
