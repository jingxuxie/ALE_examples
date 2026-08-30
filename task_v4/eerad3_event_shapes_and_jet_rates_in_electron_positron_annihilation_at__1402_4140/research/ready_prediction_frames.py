import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    concept = Path(__file__).resolve().parents[1] / 'concept_1'
    read = lambda name: json.loads((concept / name).read_text())
    privileged = read('adversary/generation_3_privileged_score.json')
    control = read('adversary/orphan_cpu_control_score.json')
    validation = read('adversary/generation_3_validation.json')
    assert privileged['passed']
    assert control['valid'] and control['cpu_seconds'] >= 2
    assert validation['all_controls_correct'] and all(validation['archive_controls'].values())
    status = read('status.json')
    status.update(name='Frame-independent five-parton kernel prediction', generation=3,
                  status='ready_for_fresh_attempt', ratchet_generations=2,
                  target=read('evaluator/hidden/quality.json'),
                  public_baseline_score=read('adversary/generation_3_baseline_score.json'),
                  private_incumbent_score=read('adversary/generation_3_incumbent_score.json'),
                  privileged_score=privileged, solvability='demonstrated',
                  counterexample_search=read('adversary/generation_2_frame_search.json'),
                  ready_at=datetime.now(timezone.utc).isoformat())
    status['target'].update(test_events=200000, cpu_seconds_max=2.4, wall_seconds_max=90)
    (concept / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print('Generation 3 validated and ready to freeze.')


if __name__ == '__main__':
    main()
