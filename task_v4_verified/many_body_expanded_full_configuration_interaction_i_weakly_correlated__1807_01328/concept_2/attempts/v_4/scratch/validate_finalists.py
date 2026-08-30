from search import *
import hashlib


records=json.loads(Path('selection_summary.json').read_text())
uniforms=assay.training_uniforms(seed=732482,samples=512)
summaries=[]
for index,record in enumerate(records[:6]):
    path=Path('finalist_%02d.json'%index)
    started=time.perf_counter()
    report=assay.evaluate(model.load_witness(path),uniforms)
    report['runtime_seconds']=time.perf_counter()-started
    report['artifact_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    report['validation_seed']=732482
    report['samples_per_family']=512
    destination='validation_finalist_%02d.json'%index
    Path(destination).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    summary=dict(candidate=str(path),report=destination,expected_core=record['expected_core'],core_score=report['core_score'],nominal_passed=report['nominal']['passed'],valid=report['valid'],passed=report['passed'],counts={family:family_report['successes'] for family,family_report in report['robustness_families'].items()},runtime_seconds=report['runtime_seconds'])
    summaries.append(summary)
    print(json.dumps(summary),flush=True)
Path('validation_summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
