# Device interface

The evaluator sends `{"op":"hello","contract":{...}}` first. Send one request,
read one reply, and repeat. A new process is used for each episode. The final
policy receives only its own file and public input files mounted at `/task`.
It cannot read hidden state, seeds, labels, other submissions or the network.
It should be self-contained; no writable persistent state across episodes is
available. The public development harness uses ordinary subprocesses and only
public cases, so it runs inside the fresh-agent sandbox without nested namespaces.
The interaction timer excludes isolated-process initialization and cleanup;
the CPU and address-space caps remain enforced by the operating system.

- `{"op":"start","source":0}` replaces the current frame with an excitation
  at a site in 0 through 31. Reply `started` includes remaining frame/query budgets.
- `{"op":"parity","mask":"0123abcd"}` queries one noiseless parity on the
  current frame. The hexadecimal string must have 1–64 digits and select at most
  64 coordinates. Coordinate zero is the least significant bit. Reply `parity`
  contains `value` equal to 0 or 1 and remaining budgets.
- `{"op":"guess","family":"RS"}` irreversibly classifies the device. Reply
  `finished` carries no correctness feedback.

There are 256 bits in 32 blocks of eight. Hidden relabeling disguises two disjoint
16-site graphs. Each graph is either the rook (`R`) or Shrikhande (`S`) graph,
as defined in the executable public simulator. The source and one echo block
each receive a uniformly chosen adjacent doublet: positions (0,1), (2,3),
(4,5), or (6,7) within that block. All whole-block parities therefore vanish.
Normally the echo is uniformly one of the source's six graph neighbors.
With hidden contamination probability 0, 1/32, or 1/16, it is instead uniformly
one of the other 31 sites. The graph, relabeling and contamination stay fixed
throughout an episode; new frames independently sample echoes and doublets.

Requests must contain exactly the documented fields. Lines above 8192 bytes,
malformed JSON, invalid masks, invalid sources, queries before a frame, more
than eight queries on one frame, and total budget violations end the episode
as incorrect. Development scores are descriptive and cannot certify the hidden
target. The policy may use any strategy consistent with this contract.
