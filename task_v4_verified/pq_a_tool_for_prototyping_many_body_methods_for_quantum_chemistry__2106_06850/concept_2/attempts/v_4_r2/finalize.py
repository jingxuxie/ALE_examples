import json
import hashlib
from pathlib import Path

candidates=[]
for filename in Path('.').glob('*.validation.json'):
    try:
        report=json.loads(filename.read_text())
    except (ValueError,OSError):
        continue
    artifact_path=filename.with_name(filename.name[:-len('.validation.json')]+'.json')
    if report.get('endpoint_feasible') and report.get('path_certified') and report.get('point_count')==243 and artifact_path.exists():
        candidates.append((report['core_score'],artifact_path,filename))
score,artifact_path,report_path=max(candidates,key=lambda row:row[0])
artifact_bytes=artifact_path.read_bytes()
report_bytes=report_path.read_bytes()
Path('submission.json').write_bytes(artifact_bytes)
Path('submission.validation.json').write_bytes(report_bytes)
selection={'source':str(artifact_path),'core_score':score,'artifact_sha256':hashlib.sha256(artifact_bytes).hexdigest()}
Path('selection.json').write_text(json.dumps(selection,indent=2))
print(json.dumps(selection),flush=True)
