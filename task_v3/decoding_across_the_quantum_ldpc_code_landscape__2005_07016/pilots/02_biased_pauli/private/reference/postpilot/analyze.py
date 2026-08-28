import sys

sys.dont_write_bytecode = True

import csv
import json
import math
import os
from pathlib import Path

POSTPILOT = Path(__file__).resolve().parent
REFERENCE = POSTPILOT.parent
ROOT = REFERENCE.parents[1]
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(ROOT / 'private'))
import bootstrap

os.environ['MPLCONFIGDIR'] = str(POSTPILOT / '.cache' / 'matplotlib')
os.environ['XDG_CACHE_HOME'] = str(POSTPILOT / '.cache')
import numpy as np
from evaluator import check_digest, grade_answer, load_npz
from geometry import canonical_probabilities, pairing
from run_audit import digest, protected_hashes, save_json

GROUPS = ('both_success', 'reference_only', 'submission_only', 'both_fail')


def outcome(case, truth, answer):
    syndrome = pairing(answer['correction_x'], answer['correction_z'], case['gx'], case['gz'])
    logical = pairing(answer['correction_x'], answer['correction_z'], truth['logical_x'], truth['logical_z'])
    consistent = np.all(syndrome == case['syndrome'], axis=1)
    successful = consistent & np.all(logical == truth['logical_signature'], axis=1)
    return successful, consistent, logical


def cost(probabilities, answer):
    labels = np.array([[0, 3], [1, 2]])[answer['correction_x'], answer['correction_z']]
    return -np.log(probabilities[np.arange(probabilities.shape[0])[None, :], labels]).sum(axis=1)


def moment_summary(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return None
    return dict(count=len(values), mean=float(values.mean()), minimum=float(values.min()),
                median=float(np.median(values)), maximum=float(values.max()))


def paired_summary(rows):
    counts = {group: sum(row['group'] == group for row in rows) for group in GROUPS}
    reference_wins, submission_wins = counts['reference_only'], counts['submission_only']
    discordant = reference_wins + submission_wins
    counts.update(shots=len(rows), reference_success=counts['both_success'] + reference_wins,
                  submission_success=counts['both_success'] + submission_wins,
                  reference_minus_submission_rate=(reference_wins - submission_wins) / len(rows))
    counts['paired_exact_two_sided_p'] = min(1., 2 * sum(math.comb(discordant, count)
        for count in range(min(reference_wins, submission_wins) + 1)) / 2 ** discordant) if discordant else 1.
    counts['likelihood_clusters'] = {}
    for group in GROUPS:
        selected = [row for row in rows if row['group'] == group]
        counts['likelihood_clusters'][group] = dict(
            counts={cluster: sum(row['likelihood_cluster'] == cluster for row in selected)
                for cluster in ('reference_joint_advantage_only', 'reference_joint_and_marginal_advantage',
                                'submission_joint_advantage', 'joint_tie')},
            joint_log_ratio_reference_over_submission=moment_summary(
                [row['joint_log_ratio_reference_over_submission'] for row in selected]),
            correlation_contribution_to_log_ratio=moment_summary(
                [row['correlation_contribution_to_log_ratio'] for row in selected]),
            canonical_y_load_zscore=moment_summary([row['canonical_y_load_zscore'] for row in selected]),
            total_error_load_zscore=moment_summary([row['total_error_load_zscore'] for row in selected]),
            same_logical_coset_count=sum(row['same_logical_coset'] for row in selected))
    return counts


def write_csv(name, rows):
    with (POSTPILOT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def main():
    directory = ROOT / 'private' / 'challenge_pool' / 'challenge'
    manifest = json.loads((directory / 'manifest.json').read_text())
    report = json.loads((POSTPILOT / 'challenge_report.json').read_text())
    execution = json.loads((POSTPILOT / 'execution_provenance.json').read_text())
    assert execution['protected_originals_unchanged'] and execution['snapshot_matches_original_before']
    isolation_records = {record['case']: record for record in json.loads((POSTPILOT / 'isolation_runs.json').read_text())}
    all_rows, families = [], {}
    for entry in manifest['cases']:
        for label in ('case', 'truth', 'strong'):
            check_digest(directory / entry[label], entry[label + '_sha256'])
        case, truth = load_npz(directory / entry['case']), load_npz(directory / entry['truth'])
        prediction_path = POSTPILOT / 'predictions' / entry['case']
        check_digest(prediction_path, isolation_records[entry['case']]['prediction_sha256'])
        submission, reference = load_npz(prediction_path), load_npz(directory / entry['strong'])
        submission_ok, submission_consistent, submission_logical = outcome(case, truth, submission)
        reference_ok, reference_consistent, reference_logical = outcome(case, truth, reference)
        metric = grade_answer(prediction_path.read_bytes(), case, truth)
        actual_case_report = next(record for record in report['cases'] if record['case'] == entry['case'])
        assert metric['success_count'] == actual_case_report['success_count']
        assert submission_consistent.all() and reference_consistent.all()
        assert reference_ok.mean() == manifest['families'][entry['family']]['strong']
        probabilities = case['pauli_probs']
        marginal_x = probabilities[:, 1] + probabilities[:, 2]
        marginal_z = probabilities[:, 3] + probabilities[:, 2]
        independent = np.column_stack(((1 - marginal_x) * (1 - marginal_z),
            marginal_x * (1 - marginal_z), marginal_x * marginal_z, (1 - marginal_x) * marginal_z))
        reference_nll, submission_nll = cost(probabilities, reference), cost(probabilities, submission)
        joint_advantage = submission_nll - reference_nll
        marginal_advantage = cost(independent, submission) - cost(independent, reference)
        canonical = canonical_probabilities(case)
        frame, permutation = case['frame'], case['permutation']
        physical_x, physical_z = truth['error_x'][:, permutation], truth['error_z'][:, permutation]
        canonical_x = physical_x * frame[:, 1, 1] ^ physical_z * frame[:, 0, 1]
        canonical_z = physical_x * frame[:, 1, 0] ^ physical_z * frame[:, 0, 0]
        y_count = (canonical_x & canonical_z).sum(axis=1)
        error_weight = (canonical_x | canonical_z).sum(axis=1)
        y_rate, error_rate = canonical[:, 2], 1 - canonical[:, 0]
        y_load = (y_count - y_rate.sum()) / np.sqrt((y_rate * (1 - y_rate)).sum())
        error_load = (error_weight - error_rate.sum()) / np.sqrt((error_rate * (1 - error_rate)).sum())
        rows = []
        for shot in range(len(submission_ok)):
            group = ('both_success' if submission_ok[shot] else 'reference_only') if reference_ok[shot] else (
                'submission_only' if submission_ok[shot] else 'both_fail')
            if joint_advantage[shot] > 1e-8:
                cluster = ('reference_joint_advantage_only' if marginal_advantage[shot] <= 1e-8
                           else 'reference_joint_and_marginal_advantage')
            else:
                cluster = 'submission_joint_advantage' if joint_advantage[shot] < -1e-8 else 'joint_tie'
            row = dict(family=entry['family'], case=entry['case'], shot=shot, group=group,
                reference_success=bool(reference_ok[shot]), submission_success=bool(submission_ok[shot]),
                reference_consistent=bool(reference_consistent[shot]), submission_consistent=bool(submission_consistent[shot]),
                reference_nll=float(reference_nll[shot]), submission_nll=float(submission_nll[shot]),
                joint_log_ratio_reference_over_submission=float(joint_advantage[shot]),
                independent_log_ratio_reference_over_submission=float(marginal_advantage[shot]),
                correlation_contribution_to_log_ratio=float(joint_advantage[shot] - marginal_advantage[shot]),
                likelihood_cluster=cluster, error_weight=int(error_weight[shot]), canonical_y_count=int(y_count[shot]),
                canonical_y_load_zscore=float(y_load[shot]), total_error_load_zscore=float(error_load[shot]),
                y_load_bin='below_minus_one' if y_load[shot] < -1 else 'above_one' if y_load[shot] > 1 else 'within_one',
                error_load_bin='below_minus_one' if error_load[shot] < -1 else 'above_one' if error_load[shot] > 1 else 'within_one',
                syndrome_weight=int(case['syndrome'][shot].sum()),
                same_logical_coset=bool(np.array_equal(reference_logical[shot], submission_logical[shot])),
                residual_logical_signature_weight_submission=int(np.count_nonzero(submission_logical[shot] ^ truth['logical_signature'][shot])))
            rows.append(row)
        families[entry['family']] = paired_summary(rows)
        families[entry['family']].update(submission_metrics=report['families'][entry['family']],
            submission_max_rss_kb=actual_case_report['max_rss_kb'],
            source_historical_cpu_seconds=manifest['families'][entry['family']]['metrics']['strong']['cpu_seconds'],
            source_memory_kb=None, source_memory_note='Not recorded for frozen reference generation')
        all_rows.extend(rows)
    summary = dict(split='unchanged existing challenge', mean_core=report['mean_core'],
        worst_family=report['worst_family'], consistency=report['consistency'],
        runtime_cpu_seconds=report['runtime_cpu_seconds'], runtime_wall_seconds=report['runtime_wall_seconds'],
        max_rss_kb=max(record['max_rss_kb'] for record in report['cases']),
        families=families, paired=paired_summary(all_rows), strata={})
    for family in families:
        for feature in ('y_load_bin', 'error_load_bin'):
            for bucket in ('below_minus_one', 'within_one', 'above_one'):
                rows = [row for row in all_rows if row['family'] == family and row[feature] == bucket]
                if rows:
                    summary['strata'][family + '/' + feature + '/' + bucket] = paired_summary(rows)
    summary['interpretation_limits'] = [
        'All 1024 shots and every reference-only win are included; no example or outcome selection.',
        'Load strata are fixed at +/-1 channel-standard-deviation, not optimized for reference wins.',
        'Representative likelihood is not logical-coset posterior mass; neither decoder computes exact coset sums.',
        'Lower NLL reference-only wins establish finite-search headroom, not absence of the correlation mechanism.',
        'Same-coset both-fail outcomes are genuine shared logical failures, not a reference-success region.',
        'This single unchanged run has a CPU-adaptive candidate search; no repeated-run cherry-picking was performed.',
        'Paired exact p values are descriptive for this fixed pool, not validation of selected subgroups.'
    ]
    summary['mechanism_audit'] = dict(central_frame_mechanism_present=True,
        central_correlation_mechanism_present=True, stabilizer_equivalence_handling_present=True,
        evidence={'frame_and_full_joint_channel': 'attempt/solve.py:33',
                  'four_state_channel_costs': 'attempt/decoder.cpp:40',
                  'coupled_four_state_bp': 'attempt/decoder.cpp:108',
                  'stabilizer_descent': 'attempt/decoder.cpp:76',
                  'osd': 'attempt/decoder.cpp:346',
                  'cpu_bounded_candidate_ensemble': 'attempt/decoder.cpp:540'},
        exact_coset_posterior_absent_in_both=True,
        source='Existing unmodified css_decode_sim conditional X/Z stage update and OSD-CS(10)',
        stronger_source_run=False,
        stronger_source_note='No new source variant or invented solver; compare the frozen applicable official reference.')
    frozen_public = json.loads((REFERENCE / 'participant_manifest.json').read_text())
    actual_public = protected_hashes()['participant']
    summary['mechanism_audit']['public_matches_initial_frozen_manifest'] = frozen_public == actual_public
    summary['mechanism_audit']['prestate_note'] = (
        'The released NumPy baseline lacks frame transfer and correlated posterior inference; '
        'the native binary BP+OSD snapshot was available. The completed submission supplies both mechanisms.')
    summary['recommendation'] = ('reject' if summary['paired']['reference_only'] <= summary['paired']['submission_only']
        else 'review paired source advantage before any further action')
    assert protected_hashes() == json.loads((POSTPILOT / 'hashes_before.json').read_text())
    summary['protected_originals_unchanged'] = True
    write_csv('shot_diagnostics.csv', all_rows)
    write_csv('reference_only.csv', [row for row in all_rows if row['group'] == 'reference_only'])
    save_json('analysis.json', summary)
    print(json.dumps({name: summary[name] for name in ('mean_core', 'worst_family', 'consistency',
        'runtime_cpu_seconds', 'runtime_wall_seconds', 'max_rss_kb', 'recommendation')}, indent=2))
    print(json.dumps({family: {name: metrics[name] for name in ('both_success', 'reference_only',
        'submission_only', 'both_fail')} for family, metrics in families.items()}, indent=2))


if __name__ == '__main__':
    main()
