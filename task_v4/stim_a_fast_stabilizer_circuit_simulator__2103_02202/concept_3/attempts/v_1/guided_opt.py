import json
import random
import sys
import time

import greedy
import pair_opt
import synthesize as syn
import three_opt
import four_opt


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    randomizer = random.Random(seed)
    data = json.loads((greedy.OUT / 'best_generalized.json').read_text())
    gates, frames = data['gates'], data['frames']
    distances, predecessors = three_opt.make_table()
    pair_table = pair_opt.make_table()
    four_tables = four_opt.load_tables() if len(sys.argv) > 3 else None
    started = time.time()
    best_depth = len(syn.schedule_generalized(gates, seed))
    best_count = len(gates)
    best_state = gates, frames
    visited = set()
    iteration, stagnant = 0, 0
    while time.time() - started < seconds:
        improvement, proposals = three_opt.windows(gates, distances, False)
        pair_improvement, pair_proposals = pair_opt.windows(gates, pair_table, False)
        four_proposals = four_opt.windows(gates, four_tables, False)[1] if four_tables else []
        if not proposals and not pair_proposals:
            break
        candidates = []
        for attempt in range(100):
            if attempt % 5 in (1, 2) and four_proposals:
                proposal = randomizer.choice(four_proposals)
                changed_gates, changed_frames = four_opt.replace(gates, frames, proposal, four_tables)
            elif attempt % 5 == 0 and pair_proposals:
                proposal = randomizer.choice(pair_proposals)
                choice = randomizer.choice(pair_table[proposal[1]][1])
                changed_gates, changed_frames = pair_opt.replace(gates, frames, proposal, choice)
            elif proposals:
                proposal = randomizer.choice(proposals)
                changed_gates, changed_frames = three_opt.replace(gates, frames, proposal, predecessors, randomizer)
            else:
                continue
            signature = tuple(map(tuple, changed_gates)), tuple(map(tuple, changed_frames))
            if signature in visited:
                continue
            depth = len(syn.schedule_generalized(changed_gates, seed))
            candidates.append((depth, len(changed_gates), randomizer.random(), changed_gates, changed_frames, signature))
        if not candidates:
            gates, frames = best_state
            visited.clear()
            continue
        depth, count, _, changed_gates, changed_frames, signature = min(candidates)
        visited.add(signature)
        if depth <= best_depth + int(stagnant > 8):
            gates, frames = changed_gates, changed_frames
        if depth < best_depth or (depth == best_depth and count < best_count):
            best_depth = pair_opt.save(changed_gates, changed_frames, seed)
            best_count = count
            best_state = changed_gates, changed_frames
            stagnant = 0
        else:
            stagnant += 1
        if stagnant % 30 == 0:
            gates, frames = best_state
        iteration += 1
        if iteration % 10 == 0:
            print('iteration', iteration, 'candidate', count, depth, 'best', best_count, best_depth, flush=True)
    pair_opt.save(*best_state, seed)


if __name__ == '__main__':
    main()
