# Final compact numerical generation

Both completely fresh generation-2 agents found valid degree-14 witnesses.
Minimum all-six RMS errors were 0.12301799642474363 and 0.09071731180520343.
Their nonuniform directed constructions improve substantially over the first
champion's broad random sampler. The stronger submission is archived as
`champions/generation_2/`; the generation-2 task/evaluator remain reproducible.

We replayed the stronger champion's actual 5,000-candidate directed search over
degrees 8,10,12,13 and two independent random streams. Only the degree, seed and
degree-matched weak initialization changed; the construction and search logic
were preserved. This is 40,000 candidate trials. The best independently checked
minimum RMS errors were 2.419e-9 at degree 8, 1.136e-6 at degree 10,
0.0003803208080512754 at degree 12, and 0.0073729225896254 at degree 13.
Every final candidate was admissible, but none reached 0.05 in all configurations.

Generation 3 fixes degree 8–12 while retaining the same dense coefficient,
contractivity, complement-accuracy, phase-guard, six-configuration and 0.05 error
requirements. This probes the remaining compact-block stability boundary rather
than allowing another replay of a degree-14 or degree-48 failure. The task is
frozen before fresh evaluation. No passing degree-8–12 witness is currently
known, and no impossibility proof is asserted. A failed fresh search supports
only hard_open_candidate unless a new in-domain witness is independently found.

There are three task generations and at most three champion generations; this
is the final numerical generation under the user's cap. The prior successes
remain successes on their original tasks, not failures under retroactive rules.
All archived source, prior agent submissions and private stress candidates are
excluded from the fresh participant mount.
