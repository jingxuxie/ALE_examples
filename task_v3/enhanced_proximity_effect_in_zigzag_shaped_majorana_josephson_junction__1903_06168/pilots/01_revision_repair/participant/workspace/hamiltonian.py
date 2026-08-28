from geometry import assemble, barrier_response


def solve_request(source, request):
    if request['version'] != 1:
        raise ValueError('Unsupported request version')
    system = assemble(source, request['geometry'])
    params = dict(source.constants, **request['model'], k_x=0)
    if request['kind'] == 'barrier':
        return dict(version=1, response=barrier_response(system, params, request['probes']))
    if request['kind'] == 'gap':
        if not request['geometry']['infinite']:
            raise ValueError('Gap requests must be periodic')
        gap = source.gap_from_band_structure(system, params, Ns=request['grid_points'])
        return dict(version=1, gap=float(gap))
    raise ValueError('Unknown request kind')
