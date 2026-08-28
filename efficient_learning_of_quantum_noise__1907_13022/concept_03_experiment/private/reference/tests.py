import json
from pathlib import Path
import tempfile
import numpy as np
from solver import walsh, simplex, fit_modes, diagnostics, marginal


def main():
    random = np.random.default_rng(901)
    probabilities = random.dirichlet(np.ones(16)) * .08
    probabilities[0] += .92
    spam = random.dirichlet(np.ones(16)) * .13
    spam[0] += .87
    depths = np.array([0,1,2,4,9,16,32])
    true_rates = walsh(probabilities)
    observations = walsh(spam)[None,:] * true_rates[None,:] ** depths[:,None]
    rates, _, _ = fit_modes(depths, observations)
    reconstructed = simplex(walsh(rates)/16)
    error = float(np.abs(reconstructed-probabilities).max())
    assert error < 1e-8, error
    query = np.zeros((1,3,4),dtype=np.uint8)
    query[0,0,0] = 1
    query[0,1,1:3] = 1
    query[0,2,3] = 1
    data = dict(blocks=np.eye(4), conditional_queries=query,parents=np.zeros((4,4),dtype=np.uint8))
    report = diagnostics(probabilities,data)
    joint = marginal(probabilities,[0,1,2,3]).reshape(2,4,2)
    direct = 0.
    for given in range(2):
        for second in range(4):
            for first in range(2):
                entry = joint[given,second,first]
                numerator = entry * joint[given].sum()
                denominator = joint[given,:,first].sum()*joint[given,second,:].sum()
                direct += entry*np.log(numerator/denominator)
    cmi_error = float(abs(direct-report['conditional_information'][0]))
    assert cmi_error < 1e-13, cmi_error
    result = dict(spam_removal_max_probability_error=error, unequal_cardinality_cmi_error=cmi_error,
                  walsh_involution_error=float(np.max(np.abs(walsh(walsh(probabilities))/16-probabilities))))
    Path(__file__).with_name('unit_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
