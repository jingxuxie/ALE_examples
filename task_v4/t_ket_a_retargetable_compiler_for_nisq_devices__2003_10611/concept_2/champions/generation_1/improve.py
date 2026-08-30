import argparse
import json
import math
import random
import time

from search import ROOT, FastRouter, InvalidWitness, schedule_witness, validate


def quality(counts):
    ordered = sorted(counts)
    return ordered[0] + sum(ordered[:12]) / 240 + sum(ordered) / 90000


def mutate(generator, schedule, edges):
    candidate = schedule[:]
    gates = [index for index, operation in enumerate(candidate) if operation[0] == "gate"]
    swaps = [index for index, operation in enumerate(candidate) if operation[0] == "swap"]
    move = generator.randrange(10)
    if move < 3:
        index = generator.choice(gates)
        candidate[index] = ("gate", *generator.choice(edges))
    elif move < 5:
        source, target = generator.sample(gates, 2)
        candidate.insert(target, candidate.pop(source))
    elif move < 7:
        first, second = generator.sample(gates, 2)
        candidate[first], candidate[second] = candidate[second], candidate[first]
    elif move == 7:
        index = generator.choice(swaps)
        candidate[index] = ("swap", *generator.choice(edges))
    elif move == 8:
        source = generator.choice(swaps)
        target = max(0, min(len(candidate)-1, source + generator.randint(-12, 12)))
        candidate.insert(target, candidate.pop(source))
    else:
        source = generator.randrange(len(candidate) - 2)
        target = min(len(candidate), source + generator.randint(2, 10))
        candidate[source:target] = reversed(candidate[source:target])
    return candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate")
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--seed", type=int, default=1221)
    parser.add_argument("--tag", default="improved")
    arguments = parser.parse_args()
    witness = json.loads((ROOT / arguments.candidate).read_text())
    graph = witness["hardware"]
    fast = FastRouter(graph)
    generator = random.Random(arguments.seed)
    schedule = [(operation[0], *operation[-2:]) for operation in witness["route"]]
    counts = fast.evaluate(witness["gates"])
    score = best_score = quality(counts)
    best_schedule = schedule[:]
    (ROOT / (arguments.tag + ".json")).write_text(json.dumps(witness, indent=2) + "\n")
    started = time.monotonic()
    iteration = accepted = valid = 0
    while time.monotonic() - started < arguments.seconds:
        iteration += 1
        if iteration % 500 == 0:
            schedule = best_schedule[:]
            score = best_score
        candidate = mutate(generator, schedule, fast.edges)
        witness = schedule_witness(graph, candidate)
        try:
            validate(witness)
        except InvalidWitness:
            continue
        valid += 1
        counts = fast.evaluate(witness["gates"])
        candidate_score = quality(counts)
        temperature = 0.12 + 0.5 * ((iteration % 500) / 500) ** 2
        if candidate_score >= score or generator.random() < math.exp((candidate_score - score) / temperature):
            schedule = candidate
            score = candidate_score
            accepted += 1
        if candidate_score > best_score:
            best_score = candidate_score
            best_schedule = candidate[:]
            (ROOT / (arguments.tag + ".json")).write_text(json.dumps(witness, indent=2) + "\n")
            print("best", iteration, "valid", valid, "accepted", accepted,
                  "score", round(best_score, 4), "min", min(counts),
                  "families", [min(counts[index:index+18]) for index in range(0, 90, 18)],
                  "time", round(time.monotonic()-started, 1), flush=True)
    print("done", arguments.tag, iteration, valid, accepted, "best", best_score, flush=True)


if __name__ == "__main__":
    main()
