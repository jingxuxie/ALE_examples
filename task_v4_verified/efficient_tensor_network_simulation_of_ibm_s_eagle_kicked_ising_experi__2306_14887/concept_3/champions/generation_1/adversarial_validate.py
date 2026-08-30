from search import *

angles = np.array(json.loads((ROOT/'pulses.json').read_text())['angles']).reshape(48)
scale = np.r_[0.025,0.025,0.015,np.full(12,0.005)]
random = np.random.default_rng(4538875)
starts = np.r_[np.load(ROOT/'worst_errors.npy')[:16]/scale,random.uniform(-1,1,(112,15))]
step = 2e-5
offsets = np.r_[np.zeros((1,15)),np.eye(15)*step,-np.eye(15)*step]
def objective(normalized):
    scores = evaluate(angles,(normalized+offsets)*scale)[0]
    return scores[0],(scores[1:16]-scores[16:])/(2*step)
adversaries = []
start = time.monotonic()
for index,initial in enumerate(starts):
    result = minimize(objective,initial,jac=True,method='L-BFGS-B',bounds=[(-1,1)]*15,
                      options=dict(maxiter=200,ftol=1e-13,gtol=1e-10))
    adversaries.append(result.x*scale)
    if index%16==15:
        print('completed',index+1,'minimum',evaluate(angles,adversaries)[0].min(),'seconds',time.monotonic()-start,flush=True)
adversaries = np.array(adversaries)
scores = evaluate(angles,adversaries)[0]
exact = fidelities(angles.reshape(24,2),scenarios_from_errors(adversaries))
report = dict(count=len(scores),minimum_fidelity=float(exact.min()),maximum_fast_exact_discrepancy=float(abs(scores-exact).max()),
              scenarios=scenarios_from_errors(adversaries),fidelities=exact.tolist())
(ROOT/'adversarial_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('EXACT ADVERSARIAL MINIMUM',exact.min(),'MAX DISCREPANCY',abs(scores-exact).max(),flush=True)
