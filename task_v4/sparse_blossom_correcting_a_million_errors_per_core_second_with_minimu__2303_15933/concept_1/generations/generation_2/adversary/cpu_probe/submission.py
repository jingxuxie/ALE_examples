import time

from baseline.submission import Decoder


started = time.process_time()
while time.process_time() - started < 2.0:
    value = sum(range(1000))
