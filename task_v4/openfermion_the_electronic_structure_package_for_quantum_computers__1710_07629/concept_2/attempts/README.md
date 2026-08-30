# Builder validation and external attempts

`baseline/` contains the exact public compiler's generated artifact and reports.
No fresh participant is launched by this builder. The main orchestrator owns
isolated participant attempts and launch metadata. Targets must remain frozen.

Do not expose this directory to participants. A baseline failure demonstrates a
resource gap, not an empirical lower bound on arbitrary synthesis methods.
