"""Official CLI anchor, never included in participant inputs."""

import sys

import numpy as np

from official import solve


if __name__ == "__main__":
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        result = solve(dict(archive))
    np.savez(sys.argv[2], **result)
