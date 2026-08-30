# Frozen tournament protocol

Three built concepts use modes A, C and D. Concept-specific targets are frozen in their contracts and status files before their first fresh launches; exact participant file hashes are captured per launch. Resource and quality thresholds cannot be silently changed after seeing an attempt.

Every fresh attempt uses the supplied `run_allowlisted_codex.sh`, explicit `ultima-alpha`, a separate ephemeral session, a read-only `participant/` tree and a previously empty writable `attempts/v_N/`. Logs, status, private labels, checker source, prior attempts and generation-time work remain outside that allowlist. Model reasoning effort is `high`. Wall time is capped at 3600 seconds, with at most ten seconds for process cleanup. Early voluntary completion is recorded, not padded to an hour.

One fresh attempt is required per concept. For the witness concept, two independent fresh attempts are scheduled, so neither has access to the other's artifact. A failed infrastructure launch is recorded separately and is not evidence of scientific hardness.

Submissions are evaluated only after fresh sessions finish. Witness artifacts are parsed without executing submission code. Code-submission evaluators run only the declared executable interface and never expose hidden labels as inputs. The main session audits scientific validity, malformed-input handling, and resource accounting.

A solved concept must be champion-ratcheted: archive its best submission, perform a broad scientifically valid private challenge search, cluster failures, and focus a new openly specified generation on a demonstrated weakness. Maximum three champion generations. Targets may be revised only in an archived, explicit new generation followed by a completely fresh attempt.

An agent failure plus a trustworthy checker, but no known passing submission, is `hard_open_candidate`. A failed agent plus an actual private passing artifact is `hard_verified_achievable`. Baseline failure or an exact target formula alone is not proof of achievability by the allowed artifact class.
