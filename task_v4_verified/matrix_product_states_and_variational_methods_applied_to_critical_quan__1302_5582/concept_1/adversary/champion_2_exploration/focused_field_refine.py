import json
import time

from harness import ROOT, launch, write_json
from focused_summary import summarize


def main():
    started = time.process_time()
    summary = summarize()
    baseline = json.loads((ROOT / "tranche_2/BATCH_ACCOUNTING.json").read_text())["parent_cpu_seconds"]
    remaining_confirmation_reserve = 180.0
    assert summary["recorded_cpu_seconds"] + baseline + remaining_confirmation_reserve + 120 < 1200
    result = launch("f2_field_softmode", "teacher", 90,
                    ROOT / "runs/f2_field_softmode/projected_even_seed/state.npz")
    write_json(ROOT / "tranche_2/FIELD_REFINE_ACCOUNTING.json", {
        "parent_cpu_seconds": time.process_time() - started,
        "solver_cpu_seconds": result["cpu_seconds"],
        "refinement_uses_full_original_nonzero_field": True})
    summarize()


if __name__ == "__main__":
    main()
