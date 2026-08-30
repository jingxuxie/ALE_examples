import json
import random
import sys
import time

import four_opt
import greedy
import pair_opt
import synthesize as syn

LAYERS = []
for moves in four_opt.MOVES:
    layers = [[move] for move in moves]
    for first, left in enumerate(moves):
        for right in moves[first + 1:]:
            if not set(left[:2]).intersection(right[:2]):
                layers.append([left, right])
    LAYERS.append(layers)


def representation(state, shape, tables):
    canonical, final_frames = four_opt.canonicalize(state)
    records, lookup = tables[shape]
    index = lookup[canonical]
    path = []
    while index:
        state_key, previous, move_index, depth, frames = records[index]
        path.append((LAYERS[shape][move_index], frames))
        index = previous
    raw = []
    for layer, frames in reversed(path):
        for move in layer:
            raw.extend(syn.generalized(*move))
        for qubit in range(4):
            code = (frames >> (qubit * 4)) & 15
            xselector, zselector = code & 3, code >> 2
            frame = (xselector & 1, zselector & 1, 0, xselector >> 1, zselector >> 1, 0)
            raw.extend((name, (qubit,)) for name in syn.FRAME_WORDS[frame])
    last = [(name, (qubit,)) for qubit, frame in enumerate(final_frames) for name in syn.FRAME_WORDS[frame]]
    raw.extend(syn.inverse_gates(last))
    return raw


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    randomizer = random.Random(seed)
    data = json.loads((greedy.OUT / 'best_generalized.json').read_text())
    gates, frames = data['gates'], data['frames']
    tables = four_opt.load_tables('four_depth_table_')
    four_opt.representation = representation
    started = time.time()
    best_depth = len(syn.schedule_generalized(gates))
    best_count = len(gates)
    best_state = gates, frames
    iteration, stagnant = 0, 0
    while time.time() - started < seconds:
        improvement, proposals = four_opt.windows(gates, tables, True, randomizer)
        if not proposals:
            break
        randomizer.shuffle(proposals)
        candidates = []
        for proposal in proposals[:40]:
            changed_gates, changed_frames = four_opt.replace(gates, frames, proposal, tables)
            depth = len(syn.schedule_generalized(changed_gates, seed))
            candidates.append((depth, len(changed_gates), randomizer.random(), changed_gates, changed_frames))
        if not candidates:
            break
        depth, count, _, changed_gates, changed_frames = min(candidates)
        if depth <= best_depth + int(stagnant > 10) and count <= best_count + 64:
            gates, frames = changed_gates, changed_frames
        if depth < best_depth or (depth == best_depth and count < best_count):
            best_depth = pair_opt.save(changed_gates, changed_frames, seed)
            best_count = count
            best_state = changed_gates, changed_frames
            stagnant = 0
        else:
            stagnant += 1
        if stagnant % 20 == 0:
            gates, frames = best_state
        iteration += 1
        if iteration % 10 == 0:
            print('iteration', iteration, 'candidate', count, depth, 'best', best_count, best_depth, flush=True)
    pair_opt.save(*best_state, seed)


if __name__ == '__main__':
    main()
