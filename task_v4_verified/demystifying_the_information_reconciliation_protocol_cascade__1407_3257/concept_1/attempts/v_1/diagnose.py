import json
from concurrent.futures import ProcessPoolExecutor

from cascade_sim import run_frame
from experiment import load_suite


def check_case(payload):
    case, policy = payload
    failed = []
    for seed in case['frame_seeds']:
        result = run_frame(case, seed, policy)
        if result['failure']:
            result = run_frame(case, seed, policy, trace=True)
            failed.append(dict(case=case, seed=seed, result=result))
    return failed


if __name__ == '__main__':
    policy = json.load(open('adaptation_candidates.json'))['first0.75_remaining1']
    with ProcessPoolExecutor(max_workers=16) as executor:
        failed = [record for records in executor.map(check_case,[(case,policy) for case in load_suite('independent',frames=4)['cases']]) for record in records]
    json.dump(failed,open('failure_diagnostics.json','w'),indent=2)
    for record in failed:
        case = record['case']
        print({key:value for key,value in case.items() if key != 'frame_seeds'},'residual',record['result']['residual_bits'])
        for step in record['result']['trace']:
            print(step['features']['pass_index'],'q_est',round(step['features']['q_est'],6),'size',step['size'],'corrected',step['corrected'],'odd',step['odd_roots'],'quiet',step['features']['quiet_passes'])
