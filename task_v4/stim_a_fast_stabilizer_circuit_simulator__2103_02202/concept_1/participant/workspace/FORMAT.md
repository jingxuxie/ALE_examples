# Interface

An instance is a JSON object with `schema="detector-compression/v1"`, `detectors`, `taps`, `budget`, `regimes`, and `channels`.

`detectors` is the number of canonical detector bits. A tap is an integer bitmask over these bits; its value is the XOR of those bits. Every tap costs one unit. All bits start at zero.

Each independent channel has `signatures` (integer masks) and `probabilities` (one probability list per regime). Bits 0 through `detectors-1` of a signature toggle detectors. Bit `detectors` toggles the logical observable. For one channel, exactly one listed branch occurs with the listed probability, or no branch occurs with the remaining probability. Branches within a channel are mutually exclusive; different channels are independent. Combine signatures by XOR. Decimal JSON probabilities define the model; scores use double precision.

There are 16–28 detector bits, 28–44 distinct nonzero taps, a budget of 5–7, 12–22 channels with 1–3 branches each, and 3–6 regimes. These are correlated stabilizer detector channels, not independent detector-bit errors. Each declared regime is available in the input; only which regime is deployed is unknown. The answer is fixed across regimes. Public examples are not the hidden instances.

An answer is `{"selected":[tap_index,...],"correction":[0,1,...]}`. Indices must be distinct, strictly increasing, and in range. Table length is exactly `2**len(selected)`. In the table index, bit `j` is the observed value of tap `selected[j]`. The logical prediction is the indexed table bit. Empty selection is legal. Risk is the probability this prediction differs from the true logical bit. Extra answer fields are ignored, never trusted as scores.

`channel.py` exposes `marginals(instance, selected)` with shape `(regimes, 2**len(selected), 2)`, `risk(instance, answer)`, and `fit_table(marginals)`. All local utilities are optional and editable only in a copied workspace. Evaluation only reads your output directory and the current instance, not your edits to provided files.
