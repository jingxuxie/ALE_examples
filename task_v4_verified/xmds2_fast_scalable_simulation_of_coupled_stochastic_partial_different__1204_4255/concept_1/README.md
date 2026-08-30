# Memory-bounded spectral representation scheduling

Release only `participant/`. The current decision is `hard_open_candidate`:
both valid fresh planners miss the fixed 20% overall improvement target, and no
passing implementation or impossibility proof is known. The private generic
portfolio also falls short. Full evidence is in `status.json` and `adversary/`.

From the complete discovery root, run the supplied baseline through the isolated
scorer with `python3 -B concept_1/evaluator/evaluate.py concept_1/participant/baseline`.
The shared isolation implementation is included in `authoring/isolation.py`.
Linux bubblewrap/user namespaces are required. The task's exact public model,
baseline, interface, and 120-second/one-CPU/1-GiB limits are in `participant/`.
