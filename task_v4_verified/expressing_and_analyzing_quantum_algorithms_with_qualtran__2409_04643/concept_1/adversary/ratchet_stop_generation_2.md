# Scheduling ratchet stopping decision

The first isolated champion passed generation 1. Its replay on 24 private graphs
across four structural families exposed substantial wide-wavefront failures;
the largest private continuation gain was 1.1371647758. Three genuine frontier
failures seeded generation 2, whose target was frozen at a 1.06 geometric-mean
cost ratio, at least 1.02 on every instance, and the same 5% peak guard.

The next completely fresh agent passed generation 2 with a 1.1933691436 core
ratio and a 1.1307430555 minimum instance ratio. Its native optimizer and full
submission are archived in `champions/generation_2/`.

A further private portfolio replays that unchanged optimizer from the winning
schedules under 24 seed/objective/temperature profiles, each with 120 seconds.
Every resulting schedule is legal. Selecting the best continuation per instance
gives an additional 1.0097363982 geometric-mean ratio, 1.0019683977 minimum
instance ratio, and 1.0211024382 maximum instance ratio. This does not supply
another gap meeting the predeclared meaningful improvement criterion. The
search records, commands and exact integer resource measurements are in
`stress_generation_2/` and `stress_second_champion.py`.

Stop after one ratchet, or two task/champion generations. The concept is
`solved`, not retained as hard. This is not a claim that the champion is globally
optimal, nor that all larger scheduling problems are easy.
