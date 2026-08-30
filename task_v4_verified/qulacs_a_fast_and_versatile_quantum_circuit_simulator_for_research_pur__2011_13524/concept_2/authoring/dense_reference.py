import numpy as np


def embed(local, qubit, qubit_count):
    operator = np.ones((1, 1), dtype=np.complex128)
    for position in reversed(range(qubit_count)):
        factor = local if position == qubit else np.eye(2, dtype=np.complex128)
        operator = np.kron(operator, factor)
    return operator


def dense_unitary(qubit_count, gates):
    result = np.eye(2 ** qubit_count, dtype=np.complex128)
    projector_zero = np.diag([1.0, 0.0]).astype(complex)
    projector_one = np.diag([0.0, 1.0]).astype(complex)
    pauli_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    for gate in gates:
        if gate["gate"] == "U3":
            cosine = np.cos(gate["theta"] / 2.0)
            sine = np.sin(gate["theta"] / 2.0)
            phase_phi = np.exp(1j * gate["phi"])
            phase_lam = np.exp(1j * gate["lambda"])
            local = np.array(
                [[cosine, -phase_lam * sine], [phase_phi * sine, phase_phi * phase_lam * cosine]]
            )
            operator = embed(local, gate["qubit"], qubit_count)
        elif gate["gate"] == "CNOT":
            inactive = embed(projector_zero, gate["control"], qubit_count)
            active = embed(projector_one, gate["control"], qubit_count)
            flip = embed(pauli_x, gate["target"], qubit_count)
            operator = inactive + active @ flip
        else:
            raise ValueError("unsupported reference gate")
        result = operator @ result
    return result
