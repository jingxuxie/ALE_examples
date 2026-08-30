import json
import sys
from experimental import calibrate, posterior_integral, send

spec = json.loads(sys.stdin.readline())['spec']

def query(action, shots):
    send({'type': 'query', 'action': action, 'shots': shots})
    return json.loads(sys.stdin.readline())['counts']

model, counts, fitted = calibrate(spec, query, return_state=True,
                                strategy=sys.argv[1] if len(sys.argv) > 1 else 'final')
rates = posterior_integral(model, counts, fitted, power=12)
send({'type': 'final', 'rates': __import__('numpy').exp(rates).tolist()})
