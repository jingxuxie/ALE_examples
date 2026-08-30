# Replay contract

The frame length is `n`. Each pass has a complete permutation, interpreted as
the ordered list of original bit positions, and a positive `block_size`.
Consecutive blocks cover the whole frame. No further randomization occurs.

At a pass boundary, register all its top-level blocks with their known Alice
parities. Repeated sets of positions are registered only once. While any known
block has odd current discrepancy parity, select one and locate an error by
bisection. Split an odd block at `floor(length/2)` using its stored ordering,
register both nonempty children, and descend into the odd child. The other
child's parity is inferred from the parent. At a singleton, correct that bit.
Repeat selection over all known blocks, including subblocks and earlier passes.
Advance to the next pass only after every known block has even discrepancy
parity. Full subblock reuse is enabled. Alice's frame can be omitted because
only parity differences are relevant to replay.

Priority `earliest` orders known odd blocks by `(origin_pass, size, insertion_id)`.
Priority `shortest` orders them by `(size, origin_pass, insertion_id)`. Passes
are zero-based and insertion IDs increase monotonically. A duplicated set
retains its first ordering, origin and ID. Bisection uses the selected block's
ordering. `initial_odd` counts odd roots of pass zero before any corrections.
`residual` and `corrected` contain sorted original bit positions.

The baseline and public replay are conveniences. The evaluator uses an
independent implementation and validates every permutation and witness value.
