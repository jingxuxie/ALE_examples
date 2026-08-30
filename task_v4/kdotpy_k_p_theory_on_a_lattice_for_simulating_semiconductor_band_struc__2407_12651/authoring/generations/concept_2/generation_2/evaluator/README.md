# Trusted witness evaluation

Run from any directory:

```
python3 evaluate.py --submission /path/to/witness.json --output /path/to/evaluation.json
```

A submission directory containing `witness.json` is also accepted. The evaluator reads bounded JSON only. It never imports or executes submitted code. `hidden/model.py` and `hidden/contract.json` are the frozen trusted physics and contract. Run `adversary/validate.py` for Hermiticity, derivative finite differences, an independent transition-sum calculation, analytic Chern/zero-window controls, and malformed-witness negative controls.

Nominal and perturbation conditions are evaluated independently from participant claims. Full Kubo quadrature is cross-checked with a gauge-invariant overlap calculation; two fine, shifted meshes must agree. A global derivative norm bound supplies a continuum lower bound on the spectral gap. The parameter-neighborhood audit is explicitly finite, not a claimed proof over a continuous box.

The scalar diagnostic score counts satisfied conditions and robustness families. Only `passed: true` establishes a valid counterexample. A partial diagnostic score is not a witness.
