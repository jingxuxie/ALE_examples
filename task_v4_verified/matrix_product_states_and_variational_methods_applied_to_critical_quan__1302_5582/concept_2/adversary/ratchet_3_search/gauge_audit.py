import time

from manybody import CONCEPT, ROOT, SixContractions, np, trusted_physics, write_json


def main():
    tensor = trusted_physics.load_tensor(CONCEPT / 'attempts' / 'v_6' / 'state.npz')
    lengths = trusted_physics.COMPOSITE_INTERVALS
    gaps = trusted_physics.COMPOSITE_GAPS
    started = time.monotonic()
    original = SixContractions(tensor, lengths, gaps)
    generator = np.random.default_rng(20260828)
    half = tensor.shape[1] // 2
    unitary = np.zeros((2 * half, 2 * half), dtype=np.complex128)
    for offset in (0, half):
        raw = generator.normal(size=(half, half)) + 1j * generator.normal(size=(half, half))
        orthogonal, triangular = np.linalg.qr(raw)
        phases = np.diag(triangular) / np.abs(np.diag(triangular))
        unitary[offset:offset + half, offset:offset + half] = orthogonal * phases[None, :]
    transformed_tensor = unitary @ tensor @ unitary.conj().T
    transformed = SixContractions(transformed_tensor, lengths, gaps)
    differences = []
    for middle in lengths:
        original_raw, original_connected = original.batch(middle)
        transformed_raw, transformed_connected = transformed.batch(middle)
        differences.append({'middle_length': middle, 'maximum_raw_difference': float(np.max(np.abs(original_raw - transformed_raw))),
                            'maximum_cumulant_difference': float(np.max(np.abs(original_connected - transformed_connected)))})
    positions = (0, 16, 112, 128, 224, 240)
    direct_original = original.direct_six(positions)
    direct_transformed = transformed.direct_six(positions)
    result = {'complex_block_unitary_gauge': True, 'unitary_defect': float(np.linalg.norm(unitary @ unitary.conj().T - np.eye(2 * half))),
              'batch_differences': differences, 'sequential_original': direct_original, 'sequential_transformed': direct_transformed,
              'elapsed_seconds': time.monotonic() - started}
    write_json(ROOT / 'complex_gauge_audit.json', result)
    if max(record['maximum_cumulant_difference'] for record in differences) > 2e-11:
        raise RuntimeError('Complex gauge covariance check failed')
    print(result, flush=True)


if __name__ == '__main__':
    main()
