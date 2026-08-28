# Launch plumbing, not scored attempts

The first launch processes for concepts 01 and 04 inherited the executor's noninteractive stdin pipe and initially logged only `Reading additional input from stdin...`. They were stopped during a launch-plumbing audit. A subsequent full-log audit showed that concept 01 had progressed to a model introduction and two read-only file-discovery commands before the stop; it produced no command results or submission files. Concept 04's log still contained only the stdin message. Therefore these are startup-only aborted invocations, not completed zero-scoring solver attempts, and they provide no hardness evidence. The stdin message alone was not sufficient to establish that all startup delay was a stdin stall. Their complete logs remain under `runs/initial`.

The launcher now sets the child stdin to `DEVNULL`, persists the process ID immediately, and excludes transient platform `.git`, `.agents`, and `.codex` directories from artifact snapshots. Fresh model attempts are recorded under `runs/tournament`, with a new full 3600-second wall budget. No submitted solver is reused.

## Evaluation report-path repair

The first completed Pauli attempt was not initially scored because the tournament collector requested a report outside that pilot's permitted output tree. The evaluator rejected that report path before executing the submitted decoder. This is an authoring/orchestration failure, not a model failure. The original diagnostic and error summary remain in `research/scores/tournament/02_biased_pauli.infrastructure-error.*`.

The collector now requests reports beneath each pilot's `private/reference/evaluations/` and copies successful reports into the tournament directory. It can replay one concept with `--concept`, without launching a new model or rerunning the other concepts. A direct Pauli replay and the corrected collector replay both score the unchanged submission. No scored input, reference anchor, public task, or submitted source was changed by this repair.
