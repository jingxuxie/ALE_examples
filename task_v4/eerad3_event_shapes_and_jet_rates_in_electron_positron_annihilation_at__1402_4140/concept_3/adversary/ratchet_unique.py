import argparse
import base64
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'adversary'))
sys.path.insert(0, str(ROOT / 'evaluator'))
from prepare_generation_2 import digest, put, snapshot_generation_one
from binary_protocol import INPUT_MAGIC, OUTPUT_MAGIC, decode, serialize
from evaluate import build, evaluate, exception_result, grade, isolated_command, limits, run

ARTIFACTS = {'incumbent': 'champions/generation_1/workspace', 'demoted': 'adversary/extended_wide',
             'adaptive': 'adversary/adaptive_wide', 'baseline': 'participant/baseline'}
POLICY = 'floor(1000*min(8,0.45*min(independent_incumbent_median_paired_ratios)))/1000'
ROBUSTNESS = {'independent_campaigns': 2, 'maximum_incumbent_median_spread': 1.30,
              'maximum_paired_relative_mad': 0.25, 'maximum_private_fraction_of_limit': 0.80}


def replace_text(path, text):
    relative = str(path.relative_to(ROOT))
    old = path.read_text() if path.exists() else None
    if old == text:
        return
    if old is None:
        patch = '*** Add File: ' + relative + '\n' + ''.join('+' + line + '\n' for line in text.splitlines())
    else:
        patch = '*** Update File: ' + relative + '\n@@\n'
        patch += ''.join('-' + line + '\n' for line in old.splitlines())
        patch += ''.join('+' + line + '\n' for line in text.splitlines())
    subprocess.run(['apply_patch'], input='*** Begin Patch\n' + patch + '*** End Patch\n',
                   text=True, check=True, cwd=ROOT)


def protected_hashes():
    names = ['evaluator/evaluate.py', 'evaluator/trusted_runner.py', 'evaluator/binary_protocol.py',
             'evaluator/hidden/oracle.py', 'evaluator/hidden/driver.f90',
             *['evaluator/hidden/pristine/' + name for name in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']]]
    return {name: digest(ROOT / name) for name in names}


def public_contract(limit):
    display = 'not yet calibrated; no fresh attempt is allowed' if limit is None else f'{limit:.3f} times the pristine baseline'
    return '''## Evaluation distribution

Generation two preserves all 104 original correctness cases and the complete
1,620-case initial light-antenna challenge, then adds 8,280 independently drawn
events. The resulting one-pass batch has 10,004 distinct momentum inputs and
18 scored families. Each of nine light-antenna strata has 1,100 cases:
balanced, hierarchical, one soft radiator, two soft radiators, soft unresolved
particles, nested collinear, and three broader-opening strata with hard,
one-soft, or two-soft radiators. There is no duplicate momentum input within
a native process, no warmup pass, and no replay loop. Every returned record
in every measured trial is checked against its numerical reference and the
physical contract; no checksum or sampled subset substitutes for those checks.

Tight internal openings reach 1e-12, radiator openings approach 1e-10,
and the broader light-cluster strata have internal openings approximately
6.3e-4..5.2e-2 with radiator openings 1e-10..1e-6. Soft suppression factors
reach 1e-14; common scales range 1e-85..1e85, in addition to the original
cases. Exact degeneracies are excluded. This stratified kernel stress mix
does not claim to reproduce cross-section frequencies; no observable or
jet-resolution cut narrows the existing mapping domain. All original quality
tolerances and orientation allowances above remain unchanged.

## Build and binary stream protocol

The external Fortran ABI above is unchanged. Only the three kernel source
files are submitted. The evaluator supplies the identical trusted binary
driver included in the workspace. Build with `make`; for the public examples:

```
python3 ../input/binary_io.py encode ../input/examples.json examples.bin
python3 ../input/binary_io.py run examples.bin output.bin --library ./mapping_kernel.so
python3 ../input/binary_io.py decode output.bin
```

All binary fields are little-endian, without padding or Fortran record markers.
Input starts with the eight-byte magic (seven ASCII bytes `ERAD3B4` and one
zero byte), then a uint32 case count N and a zero uint32 reserved word. This
16-byte header keeps binary64 arrays aligned. Four contiguous buffers follow,
in this order: momenta(4,5,N) in binary64, labels(5,N) in int32, slots(3,N)
in int32, and axis(4,N) in binary64, all Fortran column-major. There is no
interleaving of event fields. The native batch wrapper uses resident pointer
views and performs no batch allocation, zeroing, or I/O copy. Output starts
with the eight-byte magic (seven ASCII bytes `ERAD3O4` and one zero byte),
a uint32 count, and a zero uint32 reserved word, then 84 binary64 values per event
in the original array order: normalized invariants (25), mapped momenta (12),
mapped invariants (3), p3 bookkeeping (12), rotation (16), inverse (16).
There is no TIME/checksum trailer. Extra bytes, wrong counts, and malformed
headers fail. The previous ASCII examples remain readable illustrations,
but the library uses the binary layout, not the old repeat count.
The supplied wrapper exports `eerad3_batch(void *input, void *output, int32_t N)`;
both pointers address complete B4 buffers including their 16-byte headers.
The output buffer is prepopulated with the O4 header and zero records. Build
creates `mapping_kernel.so`, not a standalone executable. The public helper
forks with fresh resident shared buffers and loads the library only in the child.
The public `run` helper prepares these buffers and reports a local direct-child
CPU diagnostic; only the evaluator supplies the authoritative paired score.

## Resource contract

The production CPU limit is ''' + display + '''.
The predeclared calibration rule is the smaller of 8 and 0.45 times the
smaller of two independently measured generation-one incumbent median paired
ratios, rounded downward to 0.001. Each campaign compiles and executes new
native processes and checks all their numerical records. The two incumbent
medians must agree within a factor of 1.30, and each paired-ratio relative
median absolute deviation must be at most 25%; otherwise no target is committed.
Preparation also requires a numerically passing private feasibility control
to use at most 80% of that independently determined limit in both campaigns.
This requires more than a twofold measured throughput improvement over that
incumbent, rather than carrying over the old repetition-based 18x allowance.
The resulting numerical limit is fixed in RESOURCE.json before any fresh
generation-two attempt. It is not fitted to a private candidate's score.

Five adjacent baseline/candidate pairs alternate order on one pinned CPU.
Each native process handles the unique batch exactly once. A read-only
in-namespace supervisor measures kernel RUSAGE_CHILDREN after reaping the
native child and all adopted descendants. It subtracts only trusted child
setup performed before any submitted library is loaded. The parent prepares
fresh shared input/output arrays, then forks. Trusted child code touches all
shared pages, records its own user/system CPU, sends that fixed record through
a private pipe, and closes the pipe BEFORE loading any submitted code. The
parent receives this immutable pre-code record and subtracts it from the final
independent kernel child-CPU total. Submitted constructors, dynamic loading,
all numerical work, output stores, and descendants remain charged. The parent
never loads the submitted library. Compilation and parent staging are excluded.
This models native calls with resident arrays without charging transport or
page-table preparation to the short kernel. It is not a candidate phase timer:
candidate code cannot execute before the setup record is sealed off.
No native timer is used. The score is the median of the five actual CPU
ratios; neither denominator floors nor repeat amplification are applied.
Trusted native user CPU, system CPU, full child CPU, excluded pre-code setup CPU,
and wall time are reported separately to expose overhead or scheduling variability. Valid numerical
evaluations emit valid=true. Invalid submissions and infrastructure/measurement
errors emit valid=false, zero scores, and a distinct error_kind; infrastructure
failures do not establish numerical or performance hardness.

Compilation uses a writable scratch directory; execution mounts that same
compiled /work read-only. Every run receives fresh /tmp, /dev, PID, network,
and IPC namespaces. There is no writable state shared across native processes.
Thus within-batch input memoization has no duplicate hit and filesystem caches
cannot carry expensive answers into another trial. Submission code may not
identify hidden cases, access external data, fork subprocesses, or manipulate
timing/output. Host reference files and prior submissions are never mounted.

GNU Fortran flags remain -O2 -fno-fast-math -ffp-contract=off
-ffixed-line-length-none -std=legacy. Compilation has 45 seconds wall time.
The library build additionally uses -fPIC -shared -Wl,-z,defs.
Each native run has 35 seconds CPU, a 55-second supervisor deadline and
60-second outer wall timeout, 1 GiB address space, and bounded 32 MiB files.
'''


def stage():
    if ((ROOT / 'adversary/frozen_generation_2.json').exists()
            or (ROOT / 'adversary/generation_2_unique_preparation.json').exists()):
        raise RuntimeError('Generation two is already committed or frozen')
    snapshot, seal = snapshot_generation_one()
    archive = ROOT / 'adversary/generation_2_repeated_proposal'
    assert (archive / 'generation_2_preparation.json').is_file()
    destination = ROOT / 'adversary/unique_production_batch'
    validation = json.loads((destination / 'validation.json').read_text())
    assert validation['case_count'] == validation['distinct_momentum_inputs'] == 10004
    for name in ['cases.json', 'references.json']:
        shutil.copyfile(destination / name, ROOT / 'evaluator/hidden' / name)
    driver = (ROOT / 'evaluator/binary_driver.f90').read_text()
    assert INPUT_MAGIC == b'ERAD3B4\0' and OUTPUT_MAGIC == b'ERAD3O4\0'
    assert 'eerad3_batch' in driver and 'bind' in driver.lower()
    for name in ['participant/workspace/driver.f90', 'participant/baseline/driver.f90',
                 'evaluator/hidden/driver.f90', 'evaluator/hidden/pristine/driver.f90']:
        replace_text(ROOT / name, driver)
    makefile = ('FC = gfortran\n'
                'FFLAGS = -O2 -fno-fast-math -ffp-contract=off -ffixed-line-length-none -std=legacy\n'
                'SOURCES = kinematics.f phaseee.f eerad3lib.f\n'
                'mapping_kernel.so: $(SOURCES) driver.f90\n'
                '\t$(FC) $(FFLAGS) -fPIC -shared -Wl,-z,defs $(SOURCES) driver.f90 -o $@\n'
                '.PHONY: clean\nclean:\n\trm -f mapping_driver mapping_kernel.so *.o *.mod\n')
    for name in ['participant/workspace/Makefile', 'participant/baseline/Makefile', 'evaluator/hidden/pristine/Makefile']:
        replace_text(ROOT / name, makefile)
    interface = ROOT / 'participant/input/INTERFACE.md'
    prefix = interface.read_text().split('## Evaluation distribution')[0]
    replace_text(interface, prefix + public_contract(None))
    original = json.loads((snapshot / 'evaluator/hidden/target.json').read_text())
    target = {name: original[name] for name in ['momentum_atol', 'shell_atol', 'conservation_atol',
              'mapped_invariant_atol', 'invariant_rtol', 'invariant_atol', 'rotation_atol']}
    target.update(generation=2, revision='unique_binary_fork_v4', measurement='unique_binary_one_pass',
                  case_count=10004, family_count=18, timing_pairs=5, runtime_ratio_limit=None,
                  cpu_accounting='kernel_child_user_plus_system_minus_trusted_pre_library_setup',
                  calibration_policy=POLICY, calibration_robustness=ROBUSTNESS,
                  calibration_policy_declared_utc=datetime.now(timezone.utc).isoformat(),
                  target_fixed_utc=None, freeze_utc=None, required_sha256=protected_hashes(),
                  case_sha256=validation['case_sha256'], reference_sha256=validation['reference_sha256'])
    put(ROOT / 'evaluator/hidden/target.json', target)
    put(ROOT / 'evaluator/hidden/oracle_validation.json', {
        **validation, 'original_104_preserved': True,
        'prefix_1724_validation': 'adversary/generation_2_repeated_proposal/evaluator/hidden/oracle_validation.json'})
    put(ROOT / 'participant/input/RESOURCE.json', {'generation': 2, 'revision': 'unique_binary_fork_v4',
        'runtime_ratio_limit': None, 'status': 'awaiting_pre_attempt_calibration',
        'metric': 'median of five trusted native user+system CPU ratios; only pre-library trusted setup subtracted',
        'case_count': 10004, 'passes_per_process': 1, 'shared_writable_run_storage': False,
        'calibration_policy': target['calibration_policy'], 'freeze_utc': None})
    status = json.loads((ROOT / 'status.json').read_text())
    status.update(status='unique_binary_revision_awaiting_calibration_not_frozen',
                  target={'all_cases': 10004, 'all_families': 18, 'runtime_ratio_max': None},
                  baseline_score=None, incumbent_score=None, privileged_score=None,
                  target_sha256=digest(ROOT / 'evaluator/hidden/target.json'), target_fixed_utc=None,
                  preparation_manifest='adversary/generation_2_unique_preparation.json',
                  superseded_proposal='adversary/generation_2_repeated_proposal',
                  superseded_allocation_draft='adversary/allocating_memfd_draft',
                  superseded_child_mapping_draft='adversary/mmap_child_draft',
                  main_patch_handoff_completed=True, active_calibration_running=False,
                  fresh_generation_2_attempt_started=False)
    put(ROOT / 'status.json', status)
    print('Staged unique one-pass target; resource calibration required before any attempt', flush=True)


def controls():
    results = {}
    probe_cases = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())[:1]
    probe_references = json.loads((ROOT / 'evaluator/hidden/references.json').read_text())[:1]
    probe_target = json.loads((ROOT / 'evaluator/hidden/target.json').read_text())
    for name in ['descendant_probe', 'constructor_probe', 'unique_cache_probe', 'zero_output_probe']:
        with tempfile.TemporaryDirectory(prefix='eerad3-unique-control-') as directory:
            directory = Path(directory)
            shutil.copyfile(ROOT / 'adversary' / (name + '.c'), directory / 'probe.c')
            compiled = subprocess.run(isolated_command(directory, ['gcc', '-O2', '-fPIC', '-shared', '-Wl,-z,defs',
                                                                   '/work/probe.c', '-o', '/work/runner.so']),
                                      capture_output=True, text=True, timeout=45, preexec_fn=limits)
            if compiled.returncode:
                raise RuntimeError(compiled.stderr)
            timings = []
            for trial in range(2):
                completed = subprocess.run(isolated_command(directory, ['/usr/bin/python3', '-I', '/trusted_runner.py'], trusted=True),
                                           input=serialize(probe_cases), capture_output=True, timeout=60, preexec_fn=limits)
                if completed.returncode:
                    raise RuntimeError(completed.stderr.decode(errors='replace'))
                result = json.loads(completed.stdout)
                assert result['returncode'] == 0
                if name == 'zero_output_probe':
                    records = decode(base64.b64decode(result['stdout_b64'], validate=True), len(probe_cases))
                    assert not records.any()
                    assert set(grade(probe_cases, probe_references, records, probe_target)) == {case['id'] for case in probe_cases}
                timings.append(result['cpu_seconds'])
            if name in ['descendant_probe', 'constructor_probe']:
                assert min(timings) >= 0.14
            results[name] = {'passed': True, 'trusted_cpu_seconds': timings}
            if name == 'constructor_probe':
                results[name]['library_constructor_runs_only_in_child_and_is_charged'] = True
            if name == 'zero_output_probe':
                results[name]['early_exit_prepopulated_zero_records_rejected_by_physics'] = True
    cases = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())[:8]
    references = json.loads((ROOT / 'evaluator/hidden/references.json').read_text())[:8]
    target = json.loads((ROOT / 'evaluator/hidden/target.json').read_text())
    with tempfile.TemporaryDirectory(prefix='eerad3-binary-controls-') as directory:
        executable = build(ROOT / 'adversary/timer_interposition', Path(directory))
        records, duration = run(executable, cases)
        assert not grade(cases, references, records, target)
        changed = records.copy()
        changed[-1, 0] = 1.0
        assert cases[-1]['id'] in grade(cases, references, changed, target)
        payload = OUTPUT_MAGIC + len(cases).to_bytes(4, 'little') + bytes(4) + records.astype('<f8').tobytes()
        for malformed in [payload[:-1], payload + b'TIME 0 0\n']:
            try:
                decode(malformed, len(cases))
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed or forged trailer accepted')
    results['binary_record_and_timer_controls'] = {
        'passed': True, 'linked_timer_interposition_cannot_change_cost': True,
        'trusted_cpu_seconds': duration, 'corrupted_last_record_rejected': True,
        'truncated_binary_and_extra_time_trailer_rejected': True,
        'native_driver_contains_no_timer': 'cpu_time' not in (ROOT / 'evaluator/hidden/driver.f90').read_text().lower()}
    results['measurement_contract'] = {'passed': True, 'protocol': 'B4 inherited resident arrays, post-fork library load',
        'target_sha256': digest(ROOT / 'evaluator/hidden/target.json'), 'evaluator_sha256': protected_hashes(),
        'completed_utc': datetime.now(timezone.utc).isoformat()}
    put(ROOT / 'adversary/generation_2_unique_controls.json', results)
    print('unique binary, cache-isolation, descendant and timer controls passed', flush=True)


def predeclare():
    if ((ROOT / 'adversary/frozen_generation_2.json').exists()
            or (ROOT / 'adversary/generation_2_unique_preparation.json').exists()):
        raise RuntimeError('Cannot change a committed or frozen target')
    target_path = ROOT / 'evaluator/hidden/target.json'
    target = json.loads(target_path.read_text())
    if target['runtime_ratio_limit'] is not None:
        raise RuntimeError('Unique target is already fixed')
    target.update(calibration_policy=POLICY, calibration_robustness=ROBUSTNESS,
                  calibration_policy_declared_utc=datetime.now(timezone.utc).isoformat())
    put(target_path, target)
    interface = ROOT / 'participant/input/INTERFACE.md'
    replace_text(interface, interface.read_text().split('## Evaluation distribution')[0] + public_contract(None))
    resource_path = ROOT / 'participant/input/RESOURCE.json'
    resources = json.loads(resource_path.read_text())
    resources.update(calibration_policy=POLICY, calibration_robustness=ROBUSTNESS)
    put(resource_path, resources)
    status_path = ROOT / 'status.json'
    status = json.loads(status_path.read_text())
    status['target_sha256'] = digest(target_path)
    put(status_path, status)
    print('Two-campaign policy declared; evaluator and numerical gates unchanged', flush=True)


def campaign(repeat=False, selected=None):
    if (ROOT / 'adversary/frozen_generation_2.json').exists():
        raise RuntimeError('Cannot change a frozen target')
    target_path = ROOT / 'evaluator/hidden/target.json'
    target = json.loads(target_path.read_text())
    if target['runtime_ratio_limit'] is not None:
        raise RuntimeError('Unique target is already fixed')
    stop_path = ROOT / 'adversary/calibration_early_stop.json'
    if stop_path.exists():
        raise RuntimeError('Calibration already failed its predeclared gate; review the early-stop report')
    status_path = ROOT / 'status.json'
    status = json.loads(status_path.read_text())
    status.update(status='calibrating_unique_fork_v4_not_frozen', active_calibration_running=True,
                  calibration_campaign=2 if repeat else 1)
    put(status_path, status)
    prefix = 'unique_repeat_' if repeat else 'unique_calibration_'
    names = selected or (['incumbent', 'adaptive'] if repeat else ['incumbent', 'adaptive', 'baseline', 'demoted'])
    for name in names:
        artifact = ARTIFACTS[name]
        report_path = ROOT / 'adversary' / (prefix + name + '.json')
        source_hashes = {filename: digest(ROOT / artifact / filename)
                         for filename in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']}
        if report_path.exists():
            existing = json.loads(report_path.read_text())
            if (existing.get('valid') and existing.get('target_sha256') == digest(target_path)
                    and existing.get('source_sha256') == source_hashes):
                print(prefix + name, 'already measured in this campaign; retained', flush=True)
                continue
            raise RuntimeError('Refusing stale or failed campaign evidence: ' + str(report_path))
        started_at = datetime.now(timezone.utc).isoformat()
        print(prefix + name, 'starting independent compile and five fresh pairs', started_at, flush=True)
        try:
            result = evaluate(ROOT / artifact, calibration=True)
        except Exception as error:
            result = exception_result(error)
            put(report_path, result)
            raise RuntimeError('Calibration aborted without fixing a target: ' + result['reason']) from error
        result['artifact'] = artifact
        result.update(source_sha256=source_hashes, campaign=2 if repeat else 1,
                      started_utc=started_at, completed_utc=datetime.now(timezone.utc).isoformat())
        put(report_path, result)
        print(prefix + name, json.dumps({key: result[key] for key in ['quality_passed', 'failed_case_count', 'runtime_ratio']}), flush=True)
        if name in ['incumbent', 'adaptive']:
            ratios = [pair['ratio'] for pair in result['paired_trials']]
            median = statistics.median(ratios)
            relative_mad = statistics.median(abs(ratio - median) for ratio in ratios) / median
            incumbent = json.loads((ROOT / 'adversary/unique_calibration_incumbent.json').read_text())
            incumbent_medians = [incumbent['runtime_ratio']]
            repeat_path = ROOT / 'adversary/unique_repeat_incumbent.json'
            if repeat_path.exists():
                incumbent_medians.append(json.loads(repeat_path.read_text())['runtime_ratio'])
            maximum_possible_limit = math.floor(1000 * min(8.0, 0.45 * min(incumbent_medians))) / 1000
            reasons = []
            if not result['quality_passed']:
                reasons.append('numerical feasibility failed')
            if relative_mad > ROBUSTNESS['maximum_paired_relative_mad']:
                reasons.append('paired relative MAD exceeds the predeclared limit')
            if maximum_possible_limit <= 1.5:
                reasons.append('incumbent separation cannot support the predeclared meaningful budget')
            if max(incumbent_medians) / min(incumbent_medians) > ROBUSTNESS['maximum_incumbent_median_spread']:
                reasons.append('independent incumbent medians are not repeatable')
            if name == 'adaptive' and median > ROBUSTNESS['maximum_private_fraction_of_limit'] * maximum_possible_limit:
                reasons.append('private control lacks the predeclared budget margin')
            if reasons:
                decision = {'ready': False, 'artifact': name, 'campaign': 2 if repeat else 1,
                    'reasons': reasons, 'paired_relative_mad': relative_mad,
                    'maximum_possible_limit': maximum_possible_limit, 'target_committed': False,
                    'resource_hardness_claimed': False, 'evidence': str(report_path.relative_to(ROOT))}
                put(stop_path, decision)
                status = json.loads(status_path.read_text())
                status.update(status='calibration_no_go_predeclared_gate_failed', active_calibration_running=False,
                              freeze_ready=False, calibration_decision=decision, resource_hardness_claimed=False)
                put(status_path, status)
                raise RuntimeError('NO-GO without further noise-driven runs: ' + '; '.join(reasons))
    print('Campaign complete; no target committed', flush=True)
    status = json.loads(status_path.read_text())
    status.update(active_calibration_running=False)
    put(status_path, status)


def finalize():
    if (ROOT / 'adversary/frozen_generation_2.json').exists():
        raise RuntimeError('Cannot change a frozen target')
    target_path = ROOT / 'evaluator/hidden/target.json'
    target = json.loads(target_path.read_text())
    if target['runtime_ratio_limit'] is not None or target['calibration_policy'] != POLICY:
        raise RuntimeError('Target already fixed or policy not predeclared')
    control_results = json.loads((ROOT / 'adversary/generation_2_unique_controls.json').read_text())
    assert all(result['passed'] for result in control_results.values())
    assert control_results['measurement_contract']['target_sha256'] == digest(target_path)
    assert control_results['measurement_contract']['evaluator_sha256'] == protected_hashes()
    reports = {}
    for prefix, names in [('unique_calibration_', ARTIFACTS), ('unique_repeat_', ['incumbent', 'adaptive'])]:
        for name in names:
            result = json.loads((ROOT / 'adversary' / (prefix + name + '.json')).read_text())
            assert result['valid'] and result['target_sha256'] == digest(target_path)
            assert result['source_sha256'] == {filename: digest(ROOT / ARTIFACTS[name] / filename)
                    for filename in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']}
            reports[name if prefix == 'unique_calibration_' else name + '_repeat'] = result
    medians = [reports[name]['runtime_ratio'] for name in ['incumbent', 'incumbent_repeat']]
    limit = math.floor(1000 * min(8.0, 0.45 * min(medians))) / 1000
    robustness = {'incumbent_median_spread': max(medians) / min(medians),
                  'independent_incumbent_medians': medians, 'proposed_limit': limit, 'campaigns': {}}
    for name in ['incumbent', 'incumbent_repeat', 'adaptive', 'adaptive_repeat']:
        pairs = reports[name]['paired_trials']
        ratios = [pair['ratio'] for pair in pairs]
        median = statistics.median(ratios)
        robustness['campaigns'][name] = {
            **{field + '_max_min_ratio': max(pair[field] for pair in pairs) / min(pair[field] for pair in pairs)
               for field in ['baseline', 'candidate']},
            'paired_relative_mad': statistics.median(abs(ratio - median) for ratio in ratios) / median,
            'quality_passed': reports[name]['quality_passed'], 'median_ratio': median}
    robustness['passed'] = (limit > 1.5 and robustness['incumbent_median_spread'] <= ROBUSTNESS['maximum_incumbent_median_spread']
        and all(item['paired_relative_mad'] <= ROBUSTNESS['maximum_paired_relative_mad'] for item in robustness['campaigns'].values())
        and all(reports[name]['quality_passed'] for name in ['incumbent', 'incumbent_repeat', 'adaptive', 'adaptive_repeat'])
        and all(reports[name]['runtime_ratio'] <= ROBUSTNESS['maximum_private_fraction_of_limit'] * limit
                for name in ['adaptive', 'adaptive_repeat']))
    put(ROOT / 'adversary/unique_calibration_robustness.json', robustness)
    if not robustness['passed']:
        status_path = ROOT / 'status.json'
        status = json.loads(status_path.read_text())
        status.update(status='calibration_not_ready_no_target_committed', active_calibration_running=False,
                      freeze_ready=False, calibration_robustness=robustness,
                      resource_hardness_claimed=False)
        put(status_path, status)
        raise RuntimeError('Two-campaign numerical/performance separation is insufficient; no target committed')
    fixed_at = datetime.now(timezone.utc).isoformat()
    target.update(runtime_ratio_limit=limit, target_fixed_utc=fixed_at,
                  calibration_incumbent_ratio=reports['incumbent']['runtime_ratio'], calibration_robustness_measured=robustness,
                  calibration_evidence={name: 'adversary/' + ('unique_repeat_' + name[:-7] if name.endswith('_repeat')
                                            else 'unique_calibration_' + name) + '.json' for name in reports})
    put(target_path, target)
    interface = ROOT / 'participant/input/INTERFACE.md'
    replace_text(interface, interface.read_text().split('## Evaluation distribution')[0] + public_contract(limit))
    resource_path = ROOT / 'participant/input/RESOURCE.json'
    resources = json.loads(resource_path.read_text())
    resources.update(runtime_ratio_limit=limit, status='fixed_before_fresh_attempt_not_frozen', target_fixed_utc=fixed_at)
    put(resource_path, resources)
    for name, result in reports.items():
        result['calibration_target_sha256'] = result['target_sha256']
        result['target_sha256'] = digest(target_path)
        result['runtime_ratio_limit'] = limit
        result['runtime_score'] = min(1.0, limit / result['runtime_ratio'])
        result['passed'] = result['quality_passed'] and result['runtime_ratio'] <= limit
        result['reason'] = ('all unique-event numerical and trusted CPU gates passed' if result['passed'] else
                            'numerical gates failed' if not result['quality_passed'] else 'runtime budget exceeded')
        result['measurement_note'] = 'Pre-attempt calibration measurement, scored against the predeclared rule; only the resource limit changed.'
        put(ROOT / 'adversary' / ('generation_2_unique_' + name + '_score.json'), result)
    status = json.loads((ROOT / 'status.json').read_text())
    status.update(status='prepared_for_main_review_not_frozen',
                  freeze_ready=True, active_calibration_running=False,
                  target={'all_cases': 10004, 'all_families': 18, 'runtime_ratio_max': limit,
                          'measurement': 'unique_binary_one_pass', 'numerical_tolerances': 'unchanged from generation one'},
                  target_fixed_utc=fixed_at, target_sha256=digest(target_path),
                  baseline_score=reports['baseline'], incumbent_score=reports['incumbent'],
                  privileged_score=reports['adaptive'], independent_repeats={name: reports[name + '_repeat'] for name in ['incumbent', 'adaptive']},
                  solvability='demonstrated_private_adaptive_precision' if reports['adaptive']['passed'] else 'hard_open_candidate',
                  resource_controls='adversary/generation_2_unique_controls.json')
    put(ROOT / 'status.json', status)
    material = {str(path.relative_to(ROOT)): digest(path) for section in ['participant', 'evaluator']
                for path in sorted((ROOT / section).rglob('*')) if path.is_file() and '__pycache__' not in path.parts}
    put(ROOT / 'adversary/generation_2_unique_preparation.json', {
        'generation': 2, 'revision': 'unique_binary_fork_v4', 'not_a_generation_freeze': True,
        'target_fixed_utc': fixed_at, 'target_sha256': digest(target_path), 'sha256': material,
        'case_count': 10004, 'unique_momentum_inputs': 10004, 'passes_per_native_process': 1,
        'recipe_sha256': digest(Path(__file__)), 'generator_sha256': digest(ROOT / 'adversary/prepare_unique_batch.py'),
        'superseded_proposal': 'adversary/generation_2_repeated_proposal', 'fresh_attempts_started': 0})
    print('FIXED before fresh attempt:', limit, 'x; private adaptive passed:', reports['adaptive']['passed'], '; NOT FROZEN', flush=True)


def audit():
    snapshot, seal = snapshot_generation_one()
    manifest = json.loads((ROOT / 'adversary/generation_2_unique_preparation.json').read_text())
    for name, expected in manifest['sha256'].items():
        assert digest(ROOT / name) == expected, name
    for section in ['baseline', 'workspace']:
        for name in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']:
            relative = 'participant/' + section + '/' + name
            assert digest(ROOT / relative) == seal['sha256'][relative]
    cases = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())
    references = json.loads((ROOT / 'evaluator/hidden/references.json').read_text())
    assert cases[:104] == json.loads((snapshot / 'evaluator/hidden/cases.json').read_text())
    assert references[:104] == json.loads((snapshot / 'evaluator/hidden/references.json').read_text())
    archive = ROOT / 'adversary/generation_2_repeated_proposal/evaluator/hidden'
    assert cases[:1724] == json.loads((archive / 'cases.json').read_text())
    assert references[:1724] == json.loads((archive / 'references.json').read_text())
    assert digest(ROOT / 'evaluator/hidden/oracle.py') == seal['sha256']['evaluator/hidden/oracle.py']
    for name in ['participant/workspace/driver.f90', 'participant/baseline/driver.f90', 'evaluator/hidden/pristine/driver.f90']:
        assert digest(ROOT / name) == digest(ROOT / 'evaluator/hidden/driver.f90')
    assert len(cases) == len(references) == len({json.dumps(case['p']) for case in cases}) == 10004
    assert all(not path.is_symlink() for path in (ROOT / 'participant').rglob('*'))
    put(ROOT / 'adversary/generation_2_unique_audit.json', {'passed': True, 'generation_1_sealed_files_verified': len(seal['sha256']),
        'participant_kernel_sources_unchanged': True, 'public_driver_matches_trusted_driver': True,
        'original_104_cases_and_references_unchanged': True,
        'inherited_1724_cases_and_references_unchanged': True, 'distinct_momentum_inputs': 10004,
        'target_sha256': digest(ROOT / 'evaluator/hidden/target.json')})
    print('Unique package audit passed; original seal and kernels preserved', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['stage', 'predeclare', 'calibrate', 'calibrate-core', 'calibrate-remaining',
                                         'repeat', 'finalize', 'controls', 'audit'])
    arguments = parser.parse_args()
    {'stage': stage, 'predeclare': predeclare, 'calibrate': campaign,
     'calibrate-core': lambda: campaign(selected=['incumbent', 'adaptive']),
     'calibrate-remaining': lambda: campaign(selected=['baseline', 'demoted']), 'repeat': lambda: campaign(repeat=True),
     'finalize': finalize, 'controls': controls, 'audit': audit}[arguments.mode]()
