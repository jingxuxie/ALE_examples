from search import *
import hashlib
import math
import stat
from scipy.stats import binom


totals=json.loads(Path('independent_summary.json').read_text())
selection=json.loads(Path('selection_summary.json').read_text())
assert all(record['cases_per_family']==1536 for record in totals.values())
def quality(index):
    record=totals[str(index)]
    counts=np.arange(129)
    factors=np.minimum(1,counts/(.95*128))
    expected=sum(float(factors@binom.pmf(counts,128,record[family]/record['cases_per_family'])) for family in ('vv','full'))
    return expected,selection[index]['expected_core']
selected=max(range(3),key=quality)
source=Path('finalist_%02d.json'%selected)
destination=Path('witness.json')
destination.write_bytes(source.read_bytes())
information=destination.lstat()
assert stat.S_ISREG(information.st_mode) and information.st_size<=32768
candidate=model.load_witness(destination)
model.decode_witness(candidate)
metrics=model.compute(candidate,complete=True)
Path('nominal_metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
started=time.perf_counter()
diagnostic=assay.evaluate(candidate,assay.training_uniforms())
diagnostic['runtime_seconds']=time.perf_counter()-started
Path('diagnostic.json').write_text(json.dumps(diagnostic,indent=2,allow_nan=False)+'\n')
families={family:dict(cases=1536,required_successes=math.ceil(.95*1536),successes=totals[str(selected)][family],physically_valid_cases=0,numerically_valid_cases=0,max_numerical_error_eh=0.0) for family in ('vv','full')}
for path in totals[str(selected)]['reports']:
    report=json.loads(Path(path).read_text())
    for family in ('vv','full'):
        family_report=report['robustness_families'][family]
        families[family]['physically_valid_cases']+=family_report['physically_valid_cases']
        families[family]['numerically_valid_cases']+=family_report['numerically_valid_cases']
        families[family]['max_numerical_error_eh']=max(families[family]['max_numerical_error_eh'],family_report['max_numerical_error_eh'])
validation=dict(diagnostic_only=True,official_hidden_assay=False,passed=False,status='Nominal witness conditions met; full-coefficient robustness requirement not met.',selected_candidate='scratch/'+str(source),witness_bytes=information.st_size,witness_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),nominal_passed=diagnostic['nominal']['passed'],independent_seeds=[594503,890371,114227],samples_per_seed_per_family=512,independent_families=families,independent_reports=['scratch/'+path for path in totals[str(selected)]['reports']],selection_note='Selected using estimated finite-128 aggregate score from independent public tests; no hidden assay accessed.')
Path('validation.json').write_text(json.dumps(validation,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(selected=selected,validation=validation,nominal=diagnostic['nominal'],training_counts={family:report['successes'] for family,report in diagnostic['robustness_families'].items()})),flush=True)
