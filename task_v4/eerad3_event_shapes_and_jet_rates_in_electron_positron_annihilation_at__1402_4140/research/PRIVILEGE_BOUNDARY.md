# Generation and test separation

The research tree, all evaluator/hidden trees, all adversary and champion trees,
prior EERAD3 tasks, and other attempts are generator-only artifacts. A fresh
process is launched through the user-supplied run_allowlisted_codex.sh with
`--model ultima-alpha --effort high --task-read-only`. Its only task mounts are
that concept's participant tree and a previously empty attempts/v_N directory.
The runner independently mounts its runtime files and the minimal system profile;
it disables approvals and web search. Codex's custom permission profile defaults
network to disabled, as checked in the official permissions documentation.

No builder or reconnaissance agent counts as a participant attempt. Fresh
runner logs and resource metadata stay outside the mounted attempts/v_N tree.
The parent uses a 3600-second wall timeout and terminates the process group on
expiry. The exact model and runner hash are saved in every run record. Task and
evaluator hashes are frozen before each tournament generation.

The prediction evaluator additionally runs submitted code inside bubblewrap
with a read-only submission mount, a label-free query directory, no network,
and runtime/address-space/file-size limits. Held-out labels remain exclusively
in the trusted parent process. Its native privileged passing artifact computes
the kernel on arbitrary inputs; it is not a table of hidden labels.

An initial pre-agent stdin launch error was archived separately and excluded.
The private read-only audit subagent returned a platform error before delivering
an audit; it is also not a participant attempt. Main-session verification uses
the persisted positive/negative controls and source/physics consistency checks.

Official runner-permissions source consulted during launch verification:
https://developers.openai.com/codex/permissions
