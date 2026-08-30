import baseline_optimizer

def optimize(request):
    if request['sector'] == 'any' and not any(request['field']):
        request = dict(request, sector='even')
    return baseline_optimizer.optimize(request, pair_sweeps=12)
