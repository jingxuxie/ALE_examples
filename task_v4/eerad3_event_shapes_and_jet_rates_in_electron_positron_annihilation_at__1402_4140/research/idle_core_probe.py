import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / 'concept_3'
DRAFT = CONCEPT / 'adversary/unfrozen_throughput_draft'
sys.path.insert(0, str(DRAFT / 'evaluator'))
specification = importlib.util.spec_from_file_location('unique_evaluator', DRAFT / 'evaluator/evaluate.py')
module = importlib.util.module_from_spec(specification)
specification.loader.exec_module(module)


def cpu_sample():
    counters = {}
    for line in Path('/proc/stat').read_text().splitlines():
        fields = line.split()
        if fields and fields[0].startswith('cpu') and fields[0][3:].isdigit():
            values = list(map(int, fields[1:9]))
            counters[int(fields[0][3:])] = (sum(values), values[3] + values[4])
    return counters


def main():
    initial = cpu_sample()
    time.sleep(1)
    final = cpu_sample()
    candidates = []
    for cpu in os.sched_getaffinity(0):
        total = final[cpu][0] - initial[cpu][0]
        idle = final[cpu][1] - initial[cpu][1]
        candidates.append((idle / max(1, total), cpu))
    idle_fraction, selected = max(candidates)
    os.sched_setaffinity(0, {selected})
    report = {'selected_cpu': selected, 'initial_idle_fraction': idle_fraction, 'scores': {}}
    destination = ROOT / 'research/idle_core_probe.json'
    print('Selected CPU', selected, 'idle fraction', idle_fraction, flush=True)
    for campaign in range(1, 3):
        for label, source in [('incumbent', 'champions/generation_1/workspace'),
                              ('adaptive', 'adversary/adaptive_wide')]:
            print('Starting', campaign, label, flush=True)
            score = module.evaluate(CONCEPT / source, calibration=True)
            ratios = [trial['ratio'] for trial in score['paired_trials']]
            median = statistics.median(ratios)
            deviation = statistics.median(abs(value - median) for value in ratios) / median
            score['relative_mad'] = deviation
            report['scores'][f'{campaign}_{label}'] = score
            destination.write_text(json.dumps(report, indent=2) + '\n')
            print(campaign, label, score['quality_passed'], median, deviation, ratios, flush=True)
            if label == 'incumbent' and (deviation > 0.25 or median * 0.45 <= 1):
                print('NO-GO: incumbent instability or insufficient separation persists', flush=True)
                return
            if label == 'adaptive':
                limit = min(8, 0.45 * report['scores'][f'{campaign}_incumbent']['runtime_ratio'])
                if not score['quality_passed'] or median > limit * 0.8:
                    print('NO-GO: private feasibility margin absent', flush=True)
                    return
    print('Both independent idle-core campaigns finished; inspect fixed policy before any fresh run', flush=True)


if __name__ == '__main__':
    main()
