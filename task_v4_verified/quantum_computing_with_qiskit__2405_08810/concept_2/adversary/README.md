# Private build evidence

This directory contains privileged baseline runs, evaluator audits and build
notes, not a fresh-agent attempt. Never include it in the participant allowlist.

During pre-freeze generation, an initial one-link bottleneck and stronger mixing
filter exhausted its candidate budget before writing any instance or seed. The
final generator instead uses two-link bottlenecks and the explicit filter in
`evaluator/README.md`. Four final targets and both resource caps were then frozen
before evaluator selftests; no fresh-agent results informed this construction.
