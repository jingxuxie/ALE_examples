import csv
import json
import sys
import unittest
from pathlib import Path


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).parent / 'tests'))
    import test_limits
    import test_qualification
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_qualification)
    suite.addTest(unittest.FunctionTestCase(test_limits.test_thermal_balance))
    suite.addTest(unittest.FunctionTestCase(test_limits.test_step_boundary))
    with (output / 'validation.log').open('w') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    evidence = test_qualification.EVIDENCE
    with (output / 'validation.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['test', 'maximum_absolute_error', 'tolerance', 'passed'])
        writer.writeheader()
        writer.writerows(evidence)
    (output / 'validation.json').write_text(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures),
                                                       'errors': len(result.errors), 'successful': result.wasSuccessful()}, indent=2))
    print('Qualification tests:', result.testsRun, 'passed' if result.wasSuccessful() else 'FAILED')
    if not result.wasSuccessful():
        print((output / 'validation.log').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
