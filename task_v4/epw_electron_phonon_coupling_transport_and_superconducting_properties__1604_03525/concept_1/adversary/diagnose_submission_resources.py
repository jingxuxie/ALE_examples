import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT.parent / 'authoring'))
import evaluate
from sandbox import run_submission


def digest_tree(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--memory-mb', type=int, default=16384)
    args = parser.parse_args()
    submission = args.submission.resolve()
    before = digest_tree(submission)

    def diagnostic_runner(*positional, **keywords):
        keywords['memory_mb'] = args.memory_mb
        return run_submission(*positional, **keywords)

    evaluate.run_submission = diagnostic_runner
    hidden = ROOT / 'evaluator/hidden'
    report = evaluate.evaluate(submission, hidden / 'test_input.npz', hidden / 'test_labels.npz')
    report['quality_target_met'] = report['passed']
    report['diagnostic_only'] = True
    report['passed'] = False
    report['official_score_path'] = 'attempts/v_3.score.json'
    report['resource_change'] = {
        'official_address_space_mb': 3072,
        'diagnostic_address_space_mb': args.memory_mb,
        'unchanged': 'submission bytes, hidden observations, labels, scoring, sandbox mounts, network isolation, 110-second wall limit, four numerical threads'
    }
    report['submission_sha256'] = before
    report['submission_unchanged'] = before == digest_tree(submission)
    report['interpretation'] = 'This separates prediction quality from CUDA-linked Torch virtual-address mapping. It is not an official pass, a repaired submission, or proof that the published resource target is achievable.'
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ['runtime', 'case_losses', 'case_families', 'submission_sha256']}, allow_nan=False))


if __name__ == '__main__':
    main()
