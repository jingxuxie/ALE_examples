import json
import math
import sys


def send(message):
    print(json.dumps(message), flush=True)


def receive():
    return json.loads(sys.stdin.readline())


def reconstruct(values):
    terms = {}
    for mask in sorted(values, key=lambda item: (item.bit_count(), item)):
        terms[mask] = values[mask] - math.fsum(value for subset, value in terms.items() if subset & mask == subset)
    return terms


def solve(observation):
    values = dict(observation["values"])
    triples = [mask for mask in range(256) if mask.bit_count() == 3]
    send({"query": triples})
    values.update(receive()["values"])
    terms = reconstruct(values)
    quadruples = [mask for mask in range(256) if mask.bit_count() == 4]
    quadruples.sort(key=lambda mask: -sum(abs(terms.get(mask ^ (1 << orbital), 0.0)) for orbital in range(8) if mask & (1 << orbital)))
    send({"query": quadruples[:26]})
    values.update(receive()["values"])
    terms = reconstruct(values)
    send({"estimate": math.fsum(terms.values())})
    receive()


def main():
    while True:
        observation = receive()
        if observation["event"] == "done":
            return
        solve(observation)


if __name__ == "__main__":
    main()
