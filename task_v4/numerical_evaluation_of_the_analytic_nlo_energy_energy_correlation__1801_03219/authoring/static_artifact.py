import os
from pathlib import Path
import stat


def read_regular(path,limit=2000000):
    path = Path(path)
    descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,"rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("artifact must be a bounded regular non-symlink file")
        payload = stream.read(limit+1)
        after = os.fstat(stream.fileno())
        if len(payload) > limit or before.st_mtime_ns != after.st_mtime_ns or before.st_size != after.st_size:
            raise ValueError("artifact changed while being read")
    return payload,after
