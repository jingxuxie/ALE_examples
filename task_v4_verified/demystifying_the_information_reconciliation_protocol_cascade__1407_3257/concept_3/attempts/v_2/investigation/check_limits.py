import importlib.util
import json
import resource
import subprocess
from pathlib import Path

root = Path('/tmp/cascade-c3-g2-v2-0f0el7m5/participant')
specification = importlib.util.spec_from_file_location('development', root / 'workspace/dev_evaluate.py')
development = importlib.util.module_from_spec(specification)
specification.loader.exec_module(development)
original_popen = subprocess.Popen


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def limited_popen(*arguments, **options):
    options['preexec_fn'] = limits
    return original_popen(*arguments, **options)


development.subprocess.Popen = limited_popen
cases = json.loads((root / 'input/dev_cases.json').read_text())
results = []
for index in (2, 5, 8, 11, 14, 17, 20, 23, 26):
    result = development.run_episode(str(Path('policy.py').resolve()), cases[index])
    result['case_index'] = index
    results.append(result)
    print(index, result, flush=True)
report = dict(results=results, valid=sum(result['failure'] is None for result in results), total=len(results), peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
Path('resource_score.json').write_text(json.dumps(report, indent=2) + '\n')
