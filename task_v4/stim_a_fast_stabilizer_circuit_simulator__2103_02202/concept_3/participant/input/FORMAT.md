# circuit.json

Exactly three fields: `schema_version` (integer 1), `num_qubits` (integer 36), `layers` (array). A layer is a nonempty array of gates with disjoint qubits. Gate objects have exactly `gate` and `targets`, for example `{"gate":"H","targets":[0]}`, `{"gate":"S","targets":[0]}`, `{"gate":"CX","targets":[0,1]}`. CX lists control before target. Either direction of each undirected grid edge is allowed. No aliases, measurements, ancillas, repetitions, implicit operations, or final permutations.

Qubit `6*row+column` is at `(row,column)`. Layer 0 executes first. For resulting unitary U, `x_outputs[q]` means U X_q U† and `z_outputs[q]` means U Z_q U†. Each target string is a sign followed by 36 I/X/Y/Z letters in ascending qubit order. Y is Hermitian `[[0,-i],[i,0]]`; S is `diag(1,i)`. All 72 signed images must match. Overall global phase is irrelevant.

Every H/S/CX contributes one gate. Each CX contributes one CX. Every submitted layer containing CX contributes one entangling-depth unit. No automatic rescheduling occurs. All three acceptance bounds are in `constraints.json`.

The file must be regular, nonsymlink, UTF-8 JSON of at most 67,108,864 bytes. Duplicate/extra keys, floats, nonfinite numbers, and booleans in integer fields are rejected. Parser caps are 100,000 layers and 100,000 gates, distinct from acceptance bounds. Standard JSON Schema does not express every constraint: the exact checker additionally enforces strict integer tokens, topology, disjointness, counts, and semantics.

The public `checker.py` is an independent standard-library-only exact signed-tableau checker. The preview has no OS resource isolation. The trusted evaluator uses its own immutable instance/checker, with 10 CPU seconds, 15 wall seconds, 512 MiB address space, and one CPU core. Modifying public files never changes official acceptance.
