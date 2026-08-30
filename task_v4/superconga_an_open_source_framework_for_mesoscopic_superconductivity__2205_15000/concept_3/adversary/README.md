# Private adversarial checks

`probe.py` checks that both mounted code trees are read-only, `/tmp` and `/output`
are writable, obvious private paths are absent, and the observation keys contain
no hidden state. It is a builder-written protocol test, not a tested agent.
The integration tests also exercise a 57th query, duplicate keys, NaN strengths,
invalid sites, output after final, EOF, stderr flooding, and a wall timeout.
