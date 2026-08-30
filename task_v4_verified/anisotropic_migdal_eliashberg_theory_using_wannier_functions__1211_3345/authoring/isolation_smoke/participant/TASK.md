# Runtime isolation smoke test

This is an infrastructure test, not a scientific task. Verify that Python can import numpy and scipy. Verify that the private canary path supplied in the launch prompt cannot be read. Write only the versions and the read-denial exception name to `isolation.json` in the supplied output directory. Do not search for other files or attempt a sandbox escape.
