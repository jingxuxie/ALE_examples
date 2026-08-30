import json
import sys
import numpy as np
from search import ROOT, NAMES, write_submission

artifact = json.loads((ROOT / sys.argv[1]).read_text())
word = np.array([NAMES.index(stage['component']) for stage in artifact['stages']])
values = np.array([stage['coefficient'] for stage in artifact['stages']])
values = np.maximum((values + values[::-1]) / 2, 1e-5)
for component in range(5):
    difference = 1 - values[word == component].sum()
    positions = np.flatnonzero(word[:17] == component)
    index = positions[np.argmax(values[positions])]
    if index == 16:
        values[index] += difference
    else:
        values[index] += difference / 2
        values[32 - index] += difference / 2
assert len(word) == 33 and np.all(word == word[::-1])
assert np.all(word[:-1] != word[1:])
assert np.all(np.isfinite(values)) and values.min() >= 1e-5 and values.max() <= 1
assert np.all(values == values[::-1])
assert np.max(abs(np.bincount(word, weights=values, minlength=5) - 1)) < 1e-14
write_submission(word, values)
assert (ROOT / 'submission.json').is_file() and not (ROOT / 'submission.json').is_symlink()
assert (ROOT / 'submission.json').stat().st_size <= 32768
print('submission.json written from', sys.argv[1], flush=True)
