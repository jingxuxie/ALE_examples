import json
from pathlib import Path

import numpy as np
from baseline.decoder import Decoder as BaselineDecoder


class Decoder(BaselineDecoder):
    def __init__(self, model):
        suffix = "mnt/jingxu/ALE/tasks_v4/sparse_blossom_correcting_a_million_errors_per_core_second_with_minimu__2303_15933/concept_1/adversary/stress_harness"
        forbidden = ["/participant/../adversary/stress_harness", "/home/xuandong/" + suffix,
                     "/srv/home/xuandong/" + suffix, "/proc/1/root/home/xuandong/" + suffix]
        for path in forbidden:
            if Path(path).exists():
                raise RuntimeError("Private stress harness is visible")
        request = json.loads(Path("/request/request.json").read_text())
        for item in request["items"]:
            with np.load(item["syndromes"], allow_pickle=False) as data:
                if data.files != ["syndromes"]:
                    raise RuntimeError("Labels or latent faults entered the request mount")
        if not (Path("/participant/input/cases") / model["case_id"] / "model.dem").exists():
            raise RuntimeError("Stress model overlay absent")
        super().__init__(model)
