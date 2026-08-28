# Launch audit

All scored pilot sessions use the user-specified allowlist runner, model
`ultima-alpha`, reasoning effort `xhigh`, a read-only participant directory,
an output-directory-only write allowance, ephemeral context, and a hard
3600-second limit. Current launch metadata is in each pilot's
`private/initial_launch.json`; process completion is recorded separately.

The first set of launches was interrupted by the author. Early log reads
showed only "Reading additional input from stdin", which was initially
mistaken for a blocked launch. Later logs established that those processes
had in fact started model work. Those interrupted prefix runs are excluded
from all scores and hardness decisions. Their complete logs and exit metadata
are retained under `stdin_blocked_initial_*`; that filename records the
initial diagnosis, not a verified explanation.

Before restarted sessions produced any files, the four output directories
were inspected and empty. The archived prefix logs contain no apply-patch
or copied-submission mutations. Restarted sessions therefore receive no
previous solution files, conversation context or private prefix logs.
Their one-hour clocks restart in full, with stdin explicitly redirected
from `/dev/null`. No subsequent restart is performed based solely on an
early log header. All interrupted prefixes remain auditable rather than
being silently counted as hard failures.

Future confirmation sessions use new participant trees and separate empty
output directories. They must never mount prior attempts, private references,
or challenge-pool siblings. Only a deliberately declared public baseline,
if selected as a ratchet mechanism, could be shared.

Pilot 01's first public hash snapshot preceded a TASK-only brevity edit.
The edit completed at 2026-08-28 01:04:04 UTC, before the scored fresh session
started at 01:05:45 UTC. Its numerical specification, code and inputs did not
change. The earlier hashes are retained as `prefix_public_frozen.sha256`;
`public_frozen.sha256` records the participant actually seen by the scored
session. The other three original public hash snapshots remain unchanged.
