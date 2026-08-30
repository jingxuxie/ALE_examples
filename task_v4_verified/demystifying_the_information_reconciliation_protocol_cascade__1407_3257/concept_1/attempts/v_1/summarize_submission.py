import hashlib
import json
from pathlib import Path

from cascade_sim import load_policy
from scoring import TARGET


def summarize_saved(tag, name, policy):
    policies=json.loads(Path(f'{tag}_policies.json').read_text())
    assert policies[name]==policy
    result=json.loads(Path(f'{tag}_results.json').read_text())[name]
    families={family:dict(ratio=result['ratios'][family],candidate=result['means'][family]) for family in result['ratios']}
    normal_frames=sum(family['candidate']['frames'] for family in families.values())
    normal_failures=sum(family['candidate']['failures'] for family in families.values())
    stress=result['means']['stress']
    reliability=(normal_failures/normal_frames<=TARGET['max_overall_fer'] and
                 all(family['candidate']['fer']<=TARGET['max_family_fer'] and
                     family['candidate']['fer_upper_95']<=TARGET['max_family_wilson_upper'] for family in families.values()) and
                 stress['fer']<=TARGET['max_stress_fer'])
    passed=(reliability and result['ratio']<=1-TARGET['overall_reduction'] and
            all(family['ratio']<=1-TARGET['family_reduction'] for family in families.values()))
    return dict(overall_ratio=result['ratio'],improvement=1-result['ratio'],families=families,
                normal_frames=normal_frames,normal_failures=normal_failures,normal_fer=normal_failures/normal_frames,
                stress=stress,reliability_pass=reliability,target_pass=passed,target=TARGET)


if __name__ == '__main__':
    policy=load_policy('policy.json')
    digest=hashlib.sha256(Path('policy.json').read_bytes()).hexdigest()
    summaries={}
    sources=[('validation','first_cap_validation','first_cap8'),
             ('independent','capped_independent','first_cap8'),
             ('audit','final_audit','first_cap8')]
    for split,tag,name in sources:
        if not Path(f'{tag}_results.json').exists():
            continue
        summary=summarize_saved(tag,name,policy)
        summary.update(split=split,policy_sha256=digest,
                       method='Trusted cascade_sim.run_frame; trusted scoring.summarize; public scoring gates.')
        Path(f'{split}_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        summaries[split]=summary
        print(split,summary['target_pass'],summary['overall_ratio'],summary['normal_failures'],summary['stress']['failures'])
    Path('submission_summary.json').write_text(json.dumps(dict(policy_sha256=digest,suites=summaries),indent=2)+'\n')
