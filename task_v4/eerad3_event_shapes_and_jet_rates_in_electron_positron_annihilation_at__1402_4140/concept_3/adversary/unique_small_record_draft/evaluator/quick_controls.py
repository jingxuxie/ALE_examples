from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile

from build_package import ROOT, put
from evaluate import HIDDEN, build, run
from oracle import check


def main():
    cases = json.loads((HIDDEN/'cases.json').read_text())
    references = json.loads((HIDDEN/'references.json').read_text())
    target = json.loads((HIDDEN/'target.json').read_text())
    names = ['naive_dot','no_mapping_fallback','discard_small_invariants','identity_rotation',
             'broken_mapmomenta','wrong_branch','renormalize_only']

    def inspect(name):
        with tempfile.TemporaryDirectory(prefix='eerad3-negative-') as directory:
            executable = build(ROOT/'adversary'/name,directory)
            records,seconds = run(executable,cases,3)
        families = {}
        failures = []
        for case,reference,record in zip(cases,references,records):
            errors = check(case,reference,record,target)
            families.setdefault(case['family'],[]).append(not errors)
            if errors:
                failures.append({'id':case['id'],'checks':errors})
        scores = {name:sum(values)/len(values) for name,values in families.items()}
        result = {'core_score':sum(scores.values())/len(scores),'worst_family_score':min(scores.values()),
                  'passed':not failures,'failed_case_count':len(failures),'failures':failures,
                  'validation_mode':'numerical negative control; runtime not scored',
                  'family_scores':scores}
        print(name,result['core_score'],result['worst_family_score'],result['passed'],flush=True)
        return name,result

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(inspect,names))
    assert all(not result['passed'] for result in results.values())
    put('attempts/negative_controls.json',json.dumps(results,indent=2)+'\n')


if __name__ == '__main__':
    main()
