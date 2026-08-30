from investigate import *
from validate import validate

def main():
    candidates=sorted(set(Path('.').glob('*_best.json'))|set(Path('.').glob('*_escape_*.json'))|{Path('witness.json'),Path('baseline_witness.json')})
    records=[]
    best=None
    for path in candidates:
        try:
            document=json.loads(path.read_text())
            validation=validate(path)
            if not validation['evidence_valid']:
                continue
            coefficients=unpack(document)
            reports=guard.screen_all(coefficients)
            accepted=sum(report['accepted'] for report in reports)
            points=np.unique(np.concatenate([guard._mesh(profile) for profile in guard.PROFILES]+[guard.determinant_candidates(coefficients)]))
            shared_minimum=float(np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,points))[:,0].min())
            rank=(accepted,shared_minimum)
            record=dict(source=str(path),profiles_accepted=accepted,shared_and_mesh_minimum=shared_minimum,quotient=validation['quotient_float'])
            records.append(record)
            print(json.dumps(record),flush=True)
            if best is None or rank>best[0]:
                best=(rank,path,document,validation,reports)
        except (ValueError,KeyError,AssertionError,TypeError,FileNotFoundError) as error:
            print('SKIP',str(path),type(error).__name__,str(error)[:200],flush=True)
    assert best is not None
    rank,source,document,validation,reports=best
    simplified=dict(document)
    simplified['x']=str(Fraction(document['x']).limit_denominator(10**6))
    simplified['vector']=[str(Fraction(value).limit_denominator(10000)) for value in document['vector']]
    Path('witness.json').write_text(json.dumps(simplified,separators=(',',':'))+'\n')
    try:
        validation=validate('witness.json')
        assert validation['evidence_valid']
        document=simplified
    except (ValueError,AssertionError):
        Path('witness.json').write_text(json.dumps(document,separators=(',',':'))+'\n')
        validation=validate('witness.json')
    Path('exact_validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    screening=dict(guard_version=guard.VERSION,accepted=all(report['accepted'] for report in reports),profiles=reports)
    Path('public_guard_report.json').write_text(json.dumps(screening,indent=2)+'\n')
    summary=dict(artifact='witness.json',source_candidate=str(source),valid=validation['valid'],evidence_valid=validation['evidence_valid'],profiles_accepted=rank[0],profiles_total=3,passed=screening['accepted'],core_score=rank[0]/3,worst_family_score=int(screening['accepted']),shared_and_mesh_minimum=rank[1],normalized_rayleigh_quotient=validation['quotient_float'])
    Path('submission_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    Path('candidate_comparison.json').write_text(json.dumps(records,indent=2)+'\n')
    status='The witness passes all three public profiles.' if screening['accepted'] else f'The witness passes {rank[0]} of the three public profiles. The requested falsification was not achieved.'
    report=f'''# Final submission

## Outcome

{status}

`witness.json` is the final data artifact. It satisfies the algebraic contract and the exact negative-evidence threshold, as checked by `validate.py`. No claim of successful screening evasion is made unless `passed` is true in `submission_summary.json`.

## Exact evidence and constraints

- Degree: {validation['degree']}.
- Common denominator: {document['denominator']}.
- Rational witness point: `{document['x']}`.
- Normalized Rayleigh quotient: approximately {validation['quotient_float']:.16g}; the full exact reduced fraction is in `exact_validation.json`.
- Minimum diagonal at the witness: {validation['diagonal_min']:.16g}.
- Minimum principal two-coordinate determinant: {validation['principal_two_min']:.16g}.
- Squared commutator Frobenius norm: {validation['commutator_squared']:.16g}.
- Largest coefficient row-sum bound: {max(validation['row_bounds']):.16g}, below four.
- Artifact size: {validation['bytes']} bytes.

## Reproduction

From this output directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python validate.py witness.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python ../../participant/workspace/guard.py witness.json
```

`public_guard_report.json` contains the unmodified public screen's profile reports. `submission_summary.json` records the outcome without treating admissibility as success. `candidate_comparison.json` records the final comparison of admissible saved candidates.

## Investigation and scratch work

All search code and generated data are local to this output directory; participant assets were used read-only. The searches use single-threaded BLAS and the public guard imported from the participant assets.

The investigation covers the supplied coupled-branch baseline, sparse and dense low-rank Gram constructions, optimized local coordinate geometries, quartic branch clustering, paraunitary-filter rank-two polynomial matrices, unimodular congruences, bounded coefficient perturbations, and differential-evolution refinements of filter constructions. The `*_search.py`, `optimize_*.py`, and `*.log` files retain these experiments. `diagnose.py` separates candidate locations by principal minor. `finalize.py` selects the best saved admissible candidate by profiles accepted, then by the worst value across the shared candidates and all fixed meshes.

Final candidate source: `{source}`.
'''
    Path('REPORT.md').write_text(report)
    print('FINAL',json.dumps(summary),flush=True)

if __name__=='__main__':
    main()
