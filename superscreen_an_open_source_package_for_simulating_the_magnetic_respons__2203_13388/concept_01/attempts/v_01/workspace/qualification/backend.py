def solve(case, config='qualified'):
    if config in ('legacy', 'uncoupled', 'legacy_exact_readout'):
        from .legacy import solve as legacy_solve
        result = legacy_solve(case, config=config)
        if config == 'legacy_exact_readout':
            from .galerkin import evaluate_field
            result['field'] = evaluate_field(case.observers, case.points[case.triangles], result['current'])
        return result
    from .galerkin import solve as galerkin_solve
    return galerkin_solve(case, config=config)

CONFIGURATIONS = ['qualified', 'fixed12', 'coarse', 'refined', 'reference', 'smoothed_material', 'no_coupling', 'bare_flux_control',
                  'legacy', 'uncoupled', 'legacy_exact_readout']
DEFAULT_CONFIGURATION = 'qualified'
AVAILABLE_CONFIGURATIONS = CONFIGURATIONS + ['high_reference']
