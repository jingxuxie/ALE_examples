import json
import os
from pathlib import Path
import socket

import numpy as np
from baseline.decoder import Decoder as BaselineDecoder


class Decoder(BaselineDecoder):
    def __init__(self, model):
        suffix = "mnt/jingxu/ALE/tasks_v4/sparse_blossom_correcting_a_million_errors_per_core_second_with_minimu__2303_15933/concept_1"
        forbidden = ["/participant/../evaluator/hidden/seeds.json", "/home/xuandong/" + suffix + "/evaluator/hidden/seeds.json",
                     "/srv/home/xuandong/" + suffix + "/evaluator/hidden/seeds.json", "/home/xuandong/" + suffix + "/evaluator/evaluate.py",
                     "/proc/1/root/home/xuandong/" + suffix + "/evaluator/hidden/seeds.json"]
        for path in forbidden:
            try:
                Path(path).read_bytes()
            except (FileNotFoundError, PermissionError, NotADirectoryError):
                pass
            else:
                raise RuntimeError("SECURITY FAILURE: privileged path readable: " + path)
        if "ALE_HIDDEN_CANARY" in os.environ:
            raise RuntimeError("SECURITY FAILURE: parent environment leaked")
        try:
            child = os.fork()
        except PermissionError:
            pass
        else:
            if child == 0:
                os._exit(0)
            os.waitpid(child, 0)
            raise RuntimeError("SECURITY FAILURE: child process creation allowed")
        request = json.loads(Path("/request/request.json").read_text())
        for item in request["items"]:
            with np.load(item["syndromes"], allow_pickle=False) as data:
                if data.files != ["syndromes"]:
                    raise RuntimeError("SECURITY FAILURE: request contains more than syndromes")
        try:
            connection = socket.create_connection(("1.1.1.1", 443), timeout=0.1)
        except OSError:
            pass
        else:
            connection.close()
            raise RuntimeError("SECURITY FAILURE: outbound network available")
        super().__init__(model)
