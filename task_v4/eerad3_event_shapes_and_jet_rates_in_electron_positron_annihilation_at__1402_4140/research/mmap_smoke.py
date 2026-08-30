import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / 'concept_3'
sys.path.insert(0, str(CONCEPT / 'evaluator'))
specification = importlib.util.spec_from_file_location('mapping_evaluator', CONCEPT / 'evaluator/evaluate.py')
module = importlib.util.module_from_spec(specification)
specification.loader.exec_module(module)


def main():
    cases = json.loads((CONCEPT / 'evaluator/hidden/cases.json').read_text())
    references = json.loads((CONCEPT / 'evaluator/hidden/references.json').read_text())
    target = json.loads((CONCEPT / 'evaluator/hidden/target.json').read_text())
    report = {}
    for name in ['evaluator/hidden/pristine', 'adversary/adaptive_wide']:
        with tempfile.TemporaryDirectory(prefix='eerad3-mmap-check-') as temporary:
            directory = Path(temporary)
            for filename in module.SOURCES:
                shutil.copyfile(CONCEPT / name / filename, directory / filename)
            shutil.copyfile(CONCEPT / 'evaluator/binary_driver.f90', directory / 'driver.f90')
            command = ['gfortran', '-fPIC', '-shared', '-Wl,-z,defs', *module.FLAGS,
                       *['/work/' + filename for filename in module.SOURCES], '/work/driver.f90', '-o', '/work/runner.so']
            compiled = subprocess.run(module.isolated_command(directory, command), capture_output=True,
                                      timeout=45, preexec_fn=module.limits)
            if compiled.returncode:
                raise RuntimeError(compiled.stderr.decode(errors='replace'))
            trials = []
            for trial in range(3):
                accounting = {}
                result = module.run(directory / 'runner.so', cases, min(os.sched_getaffinity(0)), accounting)
                records, duration = result[:2]
                errors = module.grade(cases, references, records, target) if trial == 0 else None
                trials.append({'cpu_seconds': duration, 'failed_cases': len(errors) if errors is not None else None,
                               'accounting': accounting})
            report[name] = trials
            print(name, json.dumps(trials), flush=True)
    (ROOT / 'research/forked_batch_smoke.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
