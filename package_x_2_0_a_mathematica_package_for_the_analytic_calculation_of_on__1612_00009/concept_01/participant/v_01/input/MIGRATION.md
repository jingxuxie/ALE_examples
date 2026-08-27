# Release handoff

This is a benchmark-authored portable reconstruction of an analytic one-loop
workflow. It preserves the coefficient, weighted-propagator, dimensional-
continuation, local-matching, and subtraction stages. It is not a claim that the
Python starter is upstream software or that its migration faults occurred in
the original project. The original proprietary CAS is not installed or needed.

The release engineer replaced some analytic stages with sampling. Early checks
at generic spacelike scalar points looked reassuring. Later users reported that
changing the quadrature order, the regulator setting, tensor rank, routing, and
the matching scale sometimes changed conclusions. A scalar check does not
certify the whole release. The release team has not determined which of these
reports have a common cause.

`release.json` is an unlabeled acceptance campaign, not a training set. It
contains four-propagator weighted tensors, a real physical cut, a dimensional
trace/counterterm identity, infrared vertices and boxes, and local matching at
exceptional Gram geometry. The two calibration cases in `tests/test_calibration.py`
only fix normalization. No general expected output is provided.

The implementation can be repaired or replaced. Keep an independently executable
baseline snapshot or its measured outputs so the release decision rests on a
controlled before/after experiment. A numerical warning is useful evidence, but
silently returning an unchecked value is not an acceptable diagnosis.
