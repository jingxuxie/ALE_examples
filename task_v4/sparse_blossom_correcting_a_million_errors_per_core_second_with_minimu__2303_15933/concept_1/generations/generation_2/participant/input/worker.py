import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    limits = request["limits"]
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (limits["address_bytes"], limits["address_bytes"]))
    resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"] + 1, limits["cpu_seconds"] + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    participant = Path(request["participant_root"])
    submission = Path(request["submission"])
    sys.path[:0] = [str(participant / "input/runtime"), str(participant / "input"), str(participant), str(submission.parent)]
    import numpy as np
    import pymatching
    import stim
    from models import load_model
    module_spec = importlib.util.spec_from_file_location("candidate_submission", submission)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    records = []
    for item in request["items"]:
        started = time.process_time()
        model = load_model(participant / "input/cases" / item["case_id"])
        with np.load(item["syndromes"], allow_pickle=False) as data:
            syndromes = np.ascontiguousarray(data["syndromes"], dtype=np.uint8)
        decoder = module.Decoder(model)
        predictions = decoder.decode(syndromes)
        if not isinstance(predictions, np.ndarray):
            raise TypeError("decode must return a NumPy array")
        if predictions.shape != (len(syndromes), model["num_observables"]):
            raise ValueError("invalid prediction shape")
        if predictions.dtype.kind not in "biu" or not np.isin(predictions, [0, 1]).all():
            raise ValueError("predictions must be binary boolean or integer values")
        np.savez_compressed(item["predictions"], predictions=predictions.astype(np.uint8))
        records.append(dict(case_id=item["case_id"], shots=len(syndromes), cpu_seconds=time.process_time() - started))
    response = dict(cases=records, python=sys.version, numpy=np.__version__, pymatching=pymatching.__version__, stim=stim.__version__)
    Path(sys.argv[2]).write_text(json.dumps(response, indent=2) + "\n")


if __name__ == "__main__":
    main()
