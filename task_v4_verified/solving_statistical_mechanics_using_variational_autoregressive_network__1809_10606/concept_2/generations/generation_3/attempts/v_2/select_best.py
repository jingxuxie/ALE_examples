import json
from pathlib import Path

from verify import evaluate
from landscape import best_sector


def main():
    root = Path(__file__).resolve().parent
    candidates = []
    best_score = 0
    for filename in root.glob('*.json'):
        try:
            witness = json.loads(filename.read_text())
            if 'weights' not in witness:
                continue
            report = evaluate(witness)
            potential = min(score for name, score in report['scores'].items()
                            if name not in ('target_sector_mass', 'proposal_sector_mass'))
            if potential >= best_score:
                witness, sector = best_sector(witness)
                report = evaluate(witness)
            best_score = max(best_score, report['core_score'])
            candidates.append((report['core_score'], filename.name, witness, report))
        except (AssertionError, ValueError, KeyError, TypeError) as error:
            print('skip', filename.name, str(error))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    for score, name, witness, report in candidates[:15]:
        print(score, name, report['metrics'], flush=True)
    score, name, witness, report = candidates[0]
    (root / 'witness.json').write_text(json.dumps(witness, indent=2, allow_nan=False) + '\n')
    report['source_candidate'] = name
    (root / 'verification.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('SELECTED', name, score, flush=True)


if __name__ == '__main__':
    main()
