import search
import argparse
import copy
import hashlib
import json
import time
from exact import assess

def make_bank(protocol, label):
    bank = copy.deepcopy(protocol)
    seed = hashlib.sha256(label.encode('ascii')).hexdigest()
    bank['seed_hex'] = seed
    for family in bank['families']:
        offsets = []
        for member in range(32):
            uniform = []
            for site in range(12):
                text = f"{seed}|{family['name']}|{member}|{site}"
                integer = int.from_bytes(hashlib.sha256(text.encode('ascii')).digest()[:8], 'big')
                uniform.append(2.0 * integer / (2**64 - 1) - 1.0)
            uniform = search.np.array(uniform)
            offsets.append((family['amplitude_before_centering'] * (uniform - uniform.mean())).tolist())
        family['offsets'] = offsets
    return bank

def main():
    lock = (search.ROOT / '.workers.lock').open('a')
    search.fcntl.flock(lock, search.fcntl.LOCK_EX)
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', default='witness.json')
    parser.add_argument('--banks', type=int, default=8)
    parser.add_argument('--label', default='independent-holdout-20260828')
    parser.add_argument('--name', default='validation')
    arguments = parser.parse_args()
    witness = json.loads((search.ROOT / arguments.witness).read_text())
    protocol = json.loads((search.SOURCE / 'input/protocol.json').read_text())
    reports = []
    for index in range(arguments.banks + 1):
        bank = protocol if index == 0 else make_bank(protocol, f'{arguments.label}-{index}')
        started = time.monotonic()
        report = assess(witness, bank)
        report['seconds'] = time.monotonic() - started
        report['bank'] = 'public' if index == 0 else f'independent-{index}'
        reports.append(report)
        print(json.dumps({key: report[key] for key in ('bank','pass','core','worst_family','families','seconds')}), flush=True)
        (search.ROOT / (arguments.name + '.json')).write_text(json.dumps(reports, indent=2) + '\n')

if __name__ == '__main__':
    main()
