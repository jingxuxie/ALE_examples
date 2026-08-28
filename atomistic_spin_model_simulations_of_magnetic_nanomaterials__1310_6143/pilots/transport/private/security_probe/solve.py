import json
import pathlib
import sys

case = json.loads(pathlib.Path(sys.argv[1]).read_text())
result = {'case_readable': True, 'submission_readable': pathlib.Path(__file__).is_file(), 'participant_readable': pathlib.Path(case['participant_file']).is_file(), 'forbidden_reads': {}}
for name, path in case['forbidden_paths'].items():
    try:
        with open(path, 'rb') as source:
            source.read(1)
        result['forbidden_reads'][name] = True
    except OSError:
        result['forbidden_reads'][name] = False
pathlib.Path(sys.argv[2]).write_text(json.dumps(result))
