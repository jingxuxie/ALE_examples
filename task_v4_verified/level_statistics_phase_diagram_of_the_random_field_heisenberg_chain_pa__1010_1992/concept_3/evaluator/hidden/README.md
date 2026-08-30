# Trusted private replication bank

The evaluator verifies protocol.json against commitment.json before scoring.
The same commitment is published in participant/input/commitment.json.
The public protocol is not a grading fallback. All files here are private,
trusted, and participant-inaccessible. The physics helper is byte-identical
to the public helper; the probe bank is deliberately different. Do not
resample, rewrite, or expose the private protocol after commitment.
