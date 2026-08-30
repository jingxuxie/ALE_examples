import search
import validate
import concurrent.futures
import json
import time
from exact import assess

def evaluate(job):
    candidate, index, fields, orientation = job
    protocol = json.loads((search.SOURCE / 'input/protocol.json').read_text())
    bank = validate.make_bank(protocol, f'final-reliability-holdout-827162-{index}')
    report = assess(dict(schema_version=1, fields=fields, orientation=orientation), bank)
    return dict(candidate=candidate, bank=index, passed=report['pass'], core=report['core'],
                worst=report['worst_family'], families=report['families'],
                differences=[[member['signed_difference'] for member in report['members']
                              if member['family'] == family['name']] for family in bank['families']])

def main():
    lock = (search.ROOT / '.workers.lock').open('a')
    search.fcntl.flock(lock, search.fcntl.LOCK_EX)
    started = time.monotonic()
    finalists = json.loads((search.ROOT / 'selection256.json').read_text())
    selected_indices = [0, 2, 4]
    jobs = [(candidate, index, finalists[candidate]['fields'], finalists[candidate]['orientation'])
            for index in range(32) for candidate in selected_indices]
    reports = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        for report in executor.map(evaluate, jobs):
            reports.append(report)
    (search.ROOT / 'reliability_banks.json').write_text(json.dumps(reports, indent=2))
    random = search.np.random.default_rng(84771123)
    summaries = []
    for candidate in selected_indices:
        members = [report for report in reports if report['candidate'] == candidate]
        values = search.np.concatenate([search.np.array(report['differences']) for report in members], axis=1)
        means = search.np.zeros((100000, 4))
        coverages = search.np.zeros((100000, 4))
        for family in range(4):
            draws = values[family, random.integers(values.shape[1], size=(100000, 32))]
            means[:, family] = draws.mean(axis=1)
            coverages[:, family] = (draws >= .025).sum(axis=1)
        passed = (means.mean(axis=1) >= .06) & (means.min(axis=1) >= .05) & (coverages.min(axis=1) >= 24)
        summary = dict(candidate=candidate, empirical_bank_passes=sum(member['passed'] for member in members),
                       banks=len(members), bootstrap_pass_probability=float(passed.mean()),
                       means=values.mean(axis=1).tolist(), deviations=values.std(axis=1).tolist(),
                       coverage=(values >= .025).mean(axis=1).tolist(),
                       minimum_core=min(member['core'] for member in members),
                       minimum_family=min(member['worst'] for member in members))
        summaries.append(summary)
    summaries.sort(key=lambda row: row['bootstrap_pass_probability'], reverse=True)
    winner = finalists[summaries[0]['candidate']]
    witness = dict(schema_version=1, fields=winner['fields'], orientation=winner['orientation'])
    (search.ROOT / 'witness.json').write_text(json.dumps(witness, indent=2) + '\n')
    protocol = json.loads((search.SOURCE / 'input/protocol.json').read_text())
    public = assess(witness, protocol)
    result = dict(seconds=time.monotonic()-started, comparisons=summaries, selected=summaries[0]['candidate'], public=public)
    (search.ROOT / 'final_reliability.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(seconds=result['seconds'], comparisons=summaries, selected=result['selected'],
                          public_pass=public['pass'], public_core=public['core'], public_worst=public['worst_family'])), flush=True)

if __name__ == '__main__':
    main()
