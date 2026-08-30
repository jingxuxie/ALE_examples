import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
from binary_protocol import OUTPUT_MAGIC, decode, serialize
from evaluate import InvalidSubmissionError, MeasurementError, exception_result


def main():
    specification = importlib.util.spec_from_file_location('public_binary_io', ROOT / 'participant/input/binary_io.py')
    helper = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(helper)
    cases = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())
    encoded = helper.encode_cases(cases)
    assert encoded == serialize(cases)
    assert len(encoded) == 16 + 224 * len(cases)
    records = np.arange(252, dtype='<f8').reshape(3, 84)
    payload = OUTPUT_MAGIC + struct.pack('<II', 3, 0) + records.tobytes()
    assert np.array_equal(records, decode(payload, 3))
    assert np.array_equal(records, helper.decode_records(payload))
    rejected = 0
    malformed = [payload[:-1], payload + b'TIME 0 0\n',
                 payload[:12] + struct.pack('<I', 1) + payload[16:],
                 payload[:8] + struct.pack('<I', 4) + payload[12:]]
    for item in malformed:
        for decoder in [lambda value: decode(value, 3), helper.decode_records]:
            try:
                decoder(item)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError('Malformed binary record accepted')
    schemas = {}
    for name, error, expected in [
        ('compile', InvalidSubmissionError('compile_failure: test'), 'invalid_submission'),
        ('malformed_native_output', InvalidSubmissionError('Binary output byte count mismatch'), 'invalid_submission'),
        ('environment', RuntimeError('environment_error: test'), 'environment_error'),
        ('measurement', MeasurementError('Invalid trusted CPU accounting'), 'measurement_error'),
        ('timeout', subprocess.TimeoutExpired('native', 60), 'measurement_error')]:
        result = exception_result(error)
        assert result['error_kind'] == expected
        assert not result['passed'] and not result['valid'] and result['reason']
        assert all(result[key] == 0 for key in ['core_score', 'worst_family_score', 'runtime_score'])
        assert result['measurement_invalid'] == (expected != 'invalid_submission')
        schemas[name] = result
    report = {'passed': True, 'protocol': 'B4 aligned shared arrays',
              'public_encoder_matches_all_trusted_cases': len(cases), 'malformed_decoder_rejections': rejected,
              'exception_schema': schemas}
    (ROOT / 'adversary/generation_2_schema_controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print('B4 public/trusted encoding, strict output parsing, and error schemas passed')


if __name__ == '__main__':
    main()
