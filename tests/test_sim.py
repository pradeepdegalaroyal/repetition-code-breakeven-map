import numpy as np

from repmem import NoiseModel, logical_failure, per_cycle_rate


def test_noiseless_no_failure():
    nm = NoiseModel(p_gate=1e-9, p_meas=1e-9, cycle_us=1e-6)
    assert logical_failure(3, nm, 4, 200, np.random.default_rng(0)) == 0.0


def test_rate_roundtrip():
    f = (1 - (1 - 2 * 0.01) ** 5) / 2
    assert abs(per_cycle_rate(f, 5) - 0.01) < 1e-9


def test_viterbi_beats_final_decoder():
    nm = NoiseModel(p_meas=0.02)
    a = logical_failure(3, nm, 10, 3000, np.random.default_rng(1), "viterbi")
    b = logical_failure(3, nm, 10, 3000, np.random.default_rng(1), "final")
    assert a < b
