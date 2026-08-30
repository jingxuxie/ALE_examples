import importlib.util
import json
from fractions import Fraction
from pathlib import Path

from assemble import assemble


assemble()
checker_path = Path('../../participant/workspace/check.py')
specification = importlib.util.spec_from_file_location('public_checker', checker_path)
checker = importlib.util.module_from_spec(specification)
specification.loader.exec_module(checker)
report = checker.verify('../../participant/input/instances.json', 'certificate.json')
Path('check_report.json').write_text(json.dumps(report, indent=2) + '\n')
document = json.load(open('certificate.json'))
maximum_bits = 0
for certificate in document['certificates']:
    for name in ['A', 'B']:
        for matrix in certificate[name]:
            for row in matrix:
                for entry in row:
                    rational = Fraction(entry)
                    maximum_bits = max(maximum_bits, abs(rational.numerator).bit_length(), rational.denominator.bit_length())
certified = sum(case['certified'] for case in report['cases'])
lines = ['# Submission status', '', f'Exactly certified blocks: {certified} / {len(report["cases"])}.', '']
if not report['passed']:
    lines += ['This is a partial result, not a complete solution to TASK.md.',
              'The third block contains a high-precision rational approximation, not an exact positivity certificate.', '']
lines += ['## Verification', '',
          '`python ../../participant/workspace/check.py ../../participant/input/instances.json certificate.json`', '',
          f'Artifact size: {Path("certificate.json").stat().st_size} bytes.',
          f'Maximum rational numerator/denominator size: {maximum_bits} bits.', '',
          'The supplied exact checker report is saved in `check_report.json`.', '',
          '## Reconstruction', '',
          '- The first block uses recovered integer factors divided by 8.',
          '- The second block uses a three-column factorization and the exact polynomial column relation',
          '  `column_4 = (x+1) column_1 + (x^2-x+2) column_2 + (2x-1) column_3`.',
          '- The third block is transformed using exact dyadic column operations and the variable substitution `x = 2t`.',
          '- `assemble.py` reproduces the artifact from the saved reconstruction data.',
          '- All exploratory programs, intermediate factors, and logs are retained in this output directory.', '']
Path('README.md').write_text('\n'.join(lines))
print(json.dumps(report, indent=2))
print('bytes', Path('certificate.json').stat().st_size, 'max_bits', maximum_bits)
