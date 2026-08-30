# Tournament boundary

`run_tournament.py` invokes the user-supplied `run_allowlisted_codex.sh` with
the exact requested `ultima-alpha` model, high reasoning effort, ephemeral
sessions, `--task-read-only`, and a fresh empty `attempts/v_N` directory. The
prompt only names TASK.md, the writable output directory, and the 3600-second
limit; no parent research, diagnoses, or private solution material is included.
The runner disables web search and escalation and applies a minimal read
allowlist plus the participant/output mounts and Codex runtime files. Its
hash and each participant file hash are recorded at launch. Child logs reside
outside the child's writable/readable submission directory.

The parent uses a separate process group and terminates it on the wall-time
limit. Startup/transport failures are logged separately and do not establish
scientific hardness. A launcher stdin correction is recorded separately from
the first substantive attempt. The active launcher supplies `/dev/null` stdin.

The sign ratchet's v_2 supplied the prior solution as a current-champion
baseline. It is conservatively classified as a privileged assisted portfolio,
excluded from qualifying clean-room hardness evidence. The qualifying v_3 receives a
separate frozen participant snapshot containing only the original weak
baseline and the beta=0.75 contract, with no previous submission or source.
The final public sign participant is restored to this clean snapshot after
the assisted run ends. All subsequent design/prediction ratchets likewise
keep prior agents' artifacts and private failing fixtures outside participant.

The final integrity audit also detects four later scratch-file changes in the
already-excluded assisted v_2 directory; their origin is not established. Its
deadline manifest is preserved, and this run is not counted toward hardness.
All five qualifying attempts have exact current submission hashes matching
their deadline/exit manifests, and no attempt processes remain running.

Concepts 1 and 2 submit data-only JSON. Their checkers do not execute submitted
code and reject nonregular artifacts. Concept 3 submits a predictor, which is
run with a fresh Bubblewrap namespace, no network, read-only submission and
participant assets, a features-only input archive, and a temporary writable
output. Hidden labels and evaluator source are not mounted. The parent scoring
process alone reads the labels. `/etc/alternatives` and `/etc/ld.so.cache` are
read-only system runtime mounts needed by this machine's NumPy/BLAS packaging;
home directories and sibling tasks are never runtime mounts.

Only public participant directories may be delivered to a future participant.
The remainder of the package is generation/evaluation evidence, not task input.
