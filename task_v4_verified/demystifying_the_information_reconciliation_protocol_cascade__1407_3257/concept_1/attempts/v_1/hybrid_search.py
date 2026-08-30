import json
from experiment import OUTPUT, load_suite, make_policy, run_candidates, size


def hybrid(first=1.25, quiet=6, second='conditional', high_quiet=8):
    policy = make_policy(first=('estimate',first),third=('frame',.5))
    rules = []
    for frame_bits in [512,1024,2048,4096,8192]:
        rules.append(dict(when=[['pass_index','ge',3],['frame_bits','ge',frame_bits],['frame_bits','le',frame_bits],
                                ['corrected_fraction','le',2/frame_bits],['quiet_passes','lt',10]],action=dict(stop=False)))
    rules.extend([
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',14]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['corrected_fraction','ge',.01],['quiet_passes','ge',high_quiet]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['corrected_fraction','gt',0],['corrected_fraction','lt',.01],['quiet_passes','ge',quiet]],action=dict(stop=True)),
        dict(when=[['pass_index','lt',1],['latency','ge',.003],['frame_bits','ge',1024]],action=dict(size=size('estimate',.5))),
        dict(when=[['pass_index','ge',1],['pass_index','lt',2],['latency','ge',.003]],action=dict(size=size('remaining',1))),
    ])
    if second == 'conditional':
        rules.append(dict(when=[['pass_index','ge',1],['pass_index','lt',2],['last_odd_fraction','ge',.4]],action=dict(size=size('first',1))))
    else:
        rules.append(dict(when=[['pass_index','ge',1],['pass_index','lt',2]],action=dict(size=size(second,1 if second == 'remaining' else 3))))
    rules.extend([
        dict(when=[['pass_index','ge',2],['pass_index','lt',3],['corrected_fraction','ge',.01],['latency','ge',.003]],action=dict(size=size('frame',.125))),
        dict(when=[['pass_index','ge',2],['pass_index','lt',3],['corrected_fraction','ge',.01]],action=dict(size=size('frame',.25))),
    ])
    policy['rules'] = rules
    return policy


if __name__ == '__main__':
    candidates = {f'first{first}_quiet{quiet}_{second}':hybrid(first,quiet,second)
                  for first in [1,1.25] for quiet in [6,7] for second in ['conditional','remaining']}
    (OUTPUT / 'hybrid_candidates.json').write_text(json.dumps(candidates,indent=2))
    run_candidates(candidates,load_suite('dev'),tag='hybrid_dev')
