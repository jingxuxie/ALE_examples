from search import *


seeds=[594503,890371,114227]
totals={str(index):dict(vv=0,full=0,cases_per_family=0,numerical_valid=True,nominal_passed=True,max_numerical_error_eh=0.0,reports=[]) for index in range(3)}
for seed in seeds:
    uniforms=assay.training_uniforms(seed=seed,samples=512)
    for index in range(3):
        started=time.perf_counter()
        path='finalist_%02d.json'%index
        report=assay.evaluate(model.load_witness(path),uniforms)
        report['runtime_seconds']=time.perf_counter()-started
        report['validation_seed']=seed
        report['samples_per_family']=512
        destination='independent_%02d_%d.json'%(index,seed)
        Path(destination).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        total=totals[str(index)]
        total['cases_per_family']+=512
        total['numerical_valid'] &= report['valid']
        total['nominal_passed'] &= report['nominal']['passed']
        total['reports'].append(destination)
        for family in ('vv','full'):
            total[family]+=report['robustness_families'][family]['successes']
            total['max_numerical_error_eh']=max(total['max_numerical_error_eh'],report['robustness_families'][family]['max_numerical_error_eh'])
        print(json.dumps(dict(candidate=path,seed=seed,core_score=report['core_score'],totals=total)),flush=True)
        Path('independent_summary.json').write_text(json.dumps(totals,indent=2)+'\n')
