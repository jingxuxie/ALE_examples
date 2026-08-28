import hashlib
import json
from pathlib import Path

from launch_round import digest_tree


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ['quantum_bath', 'transport', 'free_energy', 'activation']


def score_summary(path):
    result = json.loads(path.read_text())
    mean = result.get('mean_core', result.get('mean_family_score', result.get('mean_score')))
    worst = result.get('worst_family', result.get('worst_family_score'))
    families = result.get('families', result.get('family_scores'))
    records = result.get('cases', result.get('results', []))
    if isinstance(families, dict):
        families = {name: value.get('score') if isinstance(value, dict) else value for name, value in families.items()}
    return dict(mean_core=mean, worst_family=worst, families=families, cases=len(records),
                path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    runs = ROOT / 'authoring/runs/initial'
    concepts = {}
    for concept in CONCEPTS:
        metadata = json.loads((runs / (concept + '.json')).read_text())
        participant = Path(metadata['participant'])
        attempt = Path(metadata['attempt'])
        record = dict(model=metadata['model'], status=metadata['status'],
                      model_seconds=metadata.get('elapsed_seconds'),
                      participant_unchanged=metadata['participant_sha256'] == digest_tree(participant),
                      submission_unchanged=metadata.get('submission_sha256') == digest_tree(attempt),
                      model_log=str((runs / (concept + '.log')).relative_to(ROOT)))
        for split in ['initial', 'challenge']:
            standard = runs / (concept + '.' + split + '.scores.json')
            concurrent = runs / (concept + '.' + split + '.parallel.scores.json')
            if standard.exists():
                record[split] = score_summary(standard)
                if concurrent.exists():
                    record[split + '_concurrent_repeat'] = score_summary(concurrent)
            elif concurrent.exists():
                record[split] = score_summary(concurrent)
        concepts[concept] = record
    rankable = [name for name, record in concepts.items() if 'initial' in record]
    rankable.sort(key=lambda name: (concepts[name]['initial']['worst_family'],
                                    concepts[name]['initial']['mean_core']))
    report = dict(concepts_built=len(CONCEPTS), concepts=concepts,
                  provisional_difficulty_order=rankable,
                  ranking_note='Lower scores first. Reference calibration differs across concepts; qualitative shortcut and substantive-failure audits remain necessary.')
    destination = ROOT / 'authoring/tournament.json'
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    for concept in rankable:
        record = concepts[concept]
        print(concept, record['initial']['mean_core'], record['initial']['worst_family'],
              record['participant_unchanged'], record['submission_unchanged'])


if __name__ == '__main__':
    main()
