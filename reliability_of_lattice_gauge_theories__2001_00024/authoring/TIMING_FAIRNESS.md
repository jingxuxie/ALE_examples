# Worker timing versus isolation startup

The initial compiler screening included two parent-process timeouts while seven
completed cases took approximately 52 seconds inside the worker. Namespace setup
had independently varied between approximately 2 and 17 seconds. The initial
parent timer included this infrastructure delay, despite a 60-second solver budget.
These two zeros are not accepted as evidence of task hardness.

The repaired evaluator gives namespace startup up to 30 additional seconds but
retains a strict 60-second worker alarm, a CPU hard limit of 62 seconds, and rejects
any result whose worker duration exceeds 60 seconds. The grace is not additional
algorithm time. Original reports remain in `*_pre_startup_grace.json`; unchanged
submissions are retried only on affected cases, and corrected reports include the
old result, new result, worker duration, and total duration. Scientific contracts,
reference anchors, and scores are unchanged. Other concepts retain their original
timing unless an explicitly recorded audit uses the same fair worker clock.
