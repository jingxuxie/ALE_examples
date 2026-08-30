# Participant workspace

Use `exact.py` as the public exact-diagonalization and scoring helper. The
frozen protocol is `../input/protocol.json`; the submission is one static
JSON object described in `../TASK.md`. Python, NumPy, and SciPy are required.
The helper sets BLAS environment limits before importing NumPy. Set them
before starting Python as well when building a custom search.

Only the witness JSON is evaluated. Modifying this helper or your local
protocol does not modify the trusted evaluator or its acceptance targets.
