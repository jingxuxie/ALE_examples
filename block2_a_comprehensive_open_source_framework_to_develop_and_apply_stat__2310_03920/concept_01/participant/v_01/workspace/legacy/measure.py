def make_probes(driver, case):
    probes = {}
    for name in ['number', 'charge', 'spin', 'current']:
        builder = driver.expr_builder()
        if name != 'current':
            sites = case['region'] if name == 'charge' else range(case['n_sites'])
            for site in sites:
                builder.add_term('cd', [site, site], 0.5 if name == 'spin' else 1)
                builder.add_term('CD', [site, site], -0.5 if name == 'spin' else 1)
        else:
            for edge in case['edges']:
                left, right = edge['sites']
                delta = int(left in case['region']) - int(right in case['region'])
                amplitude = edge['after'][0][0][0]
                for operator in ['cd', 'CD']:
                    builder.add_term(operator, [left, right], -1j * delta * amplitude)
                    builder.add_term(operator, [right, left], 1j * delta * amplitude)
        probes[name] = driver.get_mpo(builder.finalize(adjust_order=True), iprint=0)
    return probes
