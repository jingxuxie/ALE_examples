import copy
from experiment import load_suite, make_policy, size
from stopping_search import search


def inverse_policy(base, fast, slow, factor=1.5):
    policy = copy.deepcopy(base)
    rules = []
    for frame_bits in [512,1024,2048,4096,8192]:
        rules.append(dict(when=[['pass_index','ge',3],['frame_bits','ge',frame_bits],['frame_bits','le',frame_bits],
                               ['corrected_fraction','le',2/frame_bits],['quiet_passes','lt',11]],action=dict(stop=False)))
    threshold = 1/8192
    while threshold <= .19:
        rules.append(dict(when=[['pass_index','ge',3],['quiet_passes','ge',fast],['corrected_fraction','gt',0],
                               ['corrected_fraction','le',threshold],['parity_est','ge',threshold*factor]],action=dict(stop=True)))
        threshold *= 1.25
    rules.extend([
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',slow],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',14]],action=dict(stop=True)),
    ])
    rules.extend(rule for rule in base['rules'] if 'stop' not in rule['action'])
    policy['rules'] = rules
    return policy


def variants(name, base):
    return {f'{name}_fast{fast}_slow{slow}_factor{factor}':inverse_policy(base,fast,slow,factor)
            for fast in [3,4,5,6] for slow in [9,11] for factor in [1,1.5,2]}


if __name__ == '__main__':
    bases = {}
    for mixed in [False,True]:
        for third in [.25,.5]:
            base = make_policy(first=('estimate',1.5),second=('parity',3),third=('frame',third))
            base['rules'] = [
                dict(when=[['pass_index','lt',1],['latency','ge',.003],['frame_bits','ge',1024]],action=dict(size=size('estimate',.5))),
                dict(when=[['pass_index','ge',1],['pass_index','lt',2],['latency','ge',.003]],action=dict(size=size('remaining',1))),
                dict(when=[['pass_index','ge',2],['pass_index','lt',3],['latency','ge',.003]],action=dict(size=size('frame',.125))),
            ]
            if mixed:
                base['rules'].append(dict(when=[['pass_index','lt',1],['frame_bits','ge',4096],['q_est','ge',.03]],action=dict(size=size('estimate',1))))
            bases[f'mixed{int(mixed)}_third{third}'] = base
    search(bases,load_suite('dev'),'inverse_dev',variant_builder=variants)
