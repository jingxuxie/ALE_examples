from experiment import load_suite, make_policy, run_candidates
from stopping_search import stopped_policy


if __name__ == '__main__':
    candidates = {}
    for first in [.75,1,1.5]:
        for second in [('remaining',1),('parity',3)]:
            for third in [('paper_second',1),('paper_second',.5),('first',4),('first',8),('first',16),('frame',.125)]:
                name = f'first{first}_{second[0]}{second[1]}_third{third[0]}{third[1]}'
                candidates[name] = stopped_policy(make_policy(first=('estimate',first),second=second,third=third),8,14)
    run_candidates(candidates,load_suite('train'),tag='third_train')
