# Compact-counterexample ratchet

The two generation-1 fresh agents both passed at degree 48, with minimum
six-configuration RMS errors 1.1896745102401776 and 1.15975826. Their artifacts
and immutable generation-1 evaluator are archived. The stronger complete artifact
is retained as `champions/generation_1/`.

The champion's own amplitude sampler exposes a degree parameter. We ran it over
eight compactness profiles (16,20,24,28,32,36,40,44), up to 5,000 candidates each,
and independently checked its best candidates. All these profiles produced a
valid numerical failure under the unchanged non-degree requirements. The smallest
verified degree was 16, with minimum RMS error 0.10690637464579521. Thus the
original 48-degree witness was unnecessarily large, by a factor of three in
polynomial degree and corresponding controlled-signal calls.

A boundary sweep at degrees 4,8,10,12,14 exhausted the same sampler's 5,000-trial
budget per profile. None met the all-six 0.05 threshold. At degree 14 the best
verified minimum error was 0.00010789420872489848. Complete per-configuration
residual and phase-guard records distinguish real silent phase-extraction error
from invalid inputs, inaccurate completion and near-zero branches.

Generation 2 focuses this compactness failure: degree 8–14, with all other
validity and error thresholds unchanged. This targets the small-block numerical
reliability boundary rather than another large-degree replay. The target is fixed
before new fresh attempts. It is a scientific falsification/search question:
there is neither a known passing in-domain witness nor a proof of impossibility.
The degree-16 and degree-48 witnesses DO NOT establish achievability in this new
domain. If fresh agents fail, only hard_open_candidate is justified unless a
new admissible degree-8–14 witness is independently verified.

Failure cluster: backward phase-extraction conditioning with accurate outer FFT
complements; compactness limits the observed instability. No library-wide claim
about all Qualtran construction routes is inferred. No authoring candidate,
champion search code, source repository, or stress result is mounted for the new
participant. It receives only the frozen supplied method and a weak degree-12
baseline. Additional private search may continue without changing the target.
