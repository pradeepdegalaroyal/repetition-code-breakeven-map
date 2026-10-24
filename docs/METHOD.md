# Method

- **Code**: distance-d bit-flip repetition code, d-1 parity checks, 10 QEC rounds, ideal final readout (logical fails if residual error is the all-ones string).
- **Noise per cycle**: data flip probability combines Pauli-twirled T1 idling, p_idle = (1-exp(-t_cycle/T1))/2 with T1 = 50 µs, and a gate-induced flip p_gate (default 0.003); each ancilla readout flips with p_meas (default 0.02).
- **Quantum baseline**: the standard repetition code with exact minimum-weight space-time decoding (Viterbi over all 2^d cumulative-error states, log-likelihood weights).
- **Classical baselines**: (i) an unencoded qubit idling for the same cycle time (break-even reference); (ii) ablation "final": majority vote from the last syndrome only, ignoring syndrome history.
- **Metric**: per-cycle rate eps = (1-(1-2F)^(1/R))/2 from failure probability F after R rounds; ratio = eps_logical / eps_physical.
- **Experiments**: noise sweep (cycle time 0.5-4 µs × p_meas 0.005-0.1, d=3,5); ablation (decoder, d=3,5,7); gate-error sweep (0-0.1).
- **Seeds**: 4 seeds, 5000 shots each (1500 for d=7).
