from test_solver import simulate, evaluate


cases = [
    dict(seed=101, n=40, count=96, width=6, groups=3, dynamic=30),
    dict(seed=102, n=100, count=256, width=7, groups=4, dynamic=100),
    dict(seed=103, n=100, count=512, width=8, groups=3, distribution='near', noise=0.0003),
    dict(seed=104, n=80, count=256, width=6, groups=3, distribution='equal'),
    dict(seed=105, n=100, count=512, width=7, groups=3, distribution='equal'),
    dict(seed=106, n=40, count=128, width=6, groups=3, distribution='equal'),
    dict(seed=107, n=100, count=512, width=7, groups=4, distribution='equal', extra=48),
    dict(seed=108, n=100, count=512, width=7, groups=5, distribution='near', extra=48),
    dict(seed=109, n=80, count=256, width=6, groups=3, dynamic=5000, noise=0.00001),
    dict(seed=110, n=100, count=128, width=6, groups=3, dynamic=1000, noise=0.00004),
    dict(seed=111, n=60, count=100, width=6, groups=3, weight=1),
    dict(seed=112, n=100, count=320, width=7, groups=4, weight=2),
    dict(seed=113, n=100, count=192, width=7, groups=3, dynamic=1000, background=4096, noise=0.0001),
    dict(seed=114, n=60, count=128, width=6, groups=4, dynamic=200, background=2048, noise=0.0001),
    dict(seed=115, n=100, count=80, width=6, groups=3, distribution='near', noise=0.009),
    dict(seed=116, n=80, count=128, width=6, groups=4, distribution='near', noise=0.005),
    dict(seed=117, n=40, count=128, width=8, groups=3, distribution='log', noise=0.0),
]


for number, specification in enumerate(cases):
    print('CASE', number + 1, specification, flush=True)
    data, truth, identity = simulate(**specification, commuting=True)
    if specification.get('background'):
        data['recovery_floor'] = 2e-5
    evaluate(data, truth, identity)
