import json
import os
from pathlib import Path

import numpy as np
from baseline.submission import Decoder as Baseline


class Decoder(Baseline):
    def __init__(self, model):
        if os.environ.get("ALE_HIDDEN_CANARY") is not None:
            raise RuntimeError("Host environment leaked")
        for name in ["/home", "/srv/home", "/evaluator", "/hidden", "/proc/1/root/home"]:
            if Path(name).exists():
                raise RuntimeError("Private filesystem unexpectedly visible")
        if not str(np.__file__).startswith("/participant/input/runtime"):
            raise RuntimeError("Runtime is not self-contained")
        request = json.loads(Path("/request/request.json").read_text())
        for item in request["items"]:
            with np.load(item["syndromes"], allow_pickle=False) as data:
                if data.files != ["syndromes"]:
                    raise RuntimeError("Privileged fields in worker input")
        try:
            process = os.fork()
        except PermissionError:
            pass
        else:
            if process == 0:
                os._exit(1)
            os.waitpid(process, 0)
            raise RuntimeError("Process creation is not blocked")
        super().__init__(model)
