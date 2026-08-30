Run `python3 evaluate.py SUBMISSION_DIRECTORY --report REPORT.json` on a Linux
host with bubblewrap, Python 3, NumPy, and scikit-learn. The evaluator creates its
own no-network, allowlisted filesystem namespace. A restrictive outer sandbox
that forbids NETLINK_ROUTE must not enclose this command; run it on the host (or
approve the command in the outer harness). It never falls back to unsandboxed
submission execution. A namespace setup failure is an evaluator environment
error, not evidence of model hardness.

The held-out file is loaded only in the trusted parent. Its labels are omitted
from the query directory mounted in the prediction process. No generator,
native source, native library, research directory, or competing submission is
mounted. Runtime and address-space limits apply to the prediction subprocess.

`../adversary/checker_validation.json` records positive and negative scorer
controls. `../adversary/native_score.json` demonstrates achievability using a
generator-privileged source-native artifact, not a lookup of held-out labels.
