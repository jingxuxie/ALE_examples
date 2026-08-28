import bootstrap
import argparse
import numpy as np
from scipy.sparse import csr_matrix
from upstream.bposd_css_decode_sim import css_decode_sim
from geometry import canonical_probabilities, transport


def decode(case, mode='strong'):
    probabilities = canonical_probabilities(case)
    simulator = css_decode_sim.__new__(css_decode_sim)
    simulator.N = case['base_hx'].shape[1]
    simulator.hx = csr_matrix(case['base_hx'])
    simulator.hz = csr_matrix(case['base_hz'])
    simulator.channel_probs_x = probabilities[:, 1].copy()
    simulator.channel_probs_y = probabilities[:, 2].copy()
    simulator.channel_probs_z = probabilities[:, 3].copy()
    simulator.max_iter = int(simulator.N / 10)
    simulator.bp_method = 'minimum_sum'
    simulator.ms_scaling_factor = 0.625
    simulator.osd_method = 'osd_cs'
    simulator.osd_order = 10
    simulator._decoder_setup()
    marginal_x = probabilities[:, 1] + probabilities[:, 2]
    marginal_z = probabilities[:, 3] + probabilities[:, 2]
    direction = 'x->z' if marginal_x.mean() <= marginal_z.mean() else 'z->x'
    row_boundary = case['base_hx'].shape[0]
    correction_x = np.empty((len(case['syndrome']), simulator.N), dtype=np.uint8)
    correction_z = np.empty_like(correction_x)
    for shot, syndrome in enumerate(case['syndrome']):
        simulator.bpd_x.update_channel_probs(marginal_x)
        simulator.bpd_z.update_channel_probs(marginal_z)
        if direction == 'x->z':
            simulator.bpd_x.decode(syndrome[row_boundary:])
            if mode != 'independent':
                simulator._channel_update(direction)
            simulator.bpd_z.decode(syndrome[:row_boundary])
        else:
            simulator.bpd_z.decode(syndrome[:row_boundary])
            if mode != 'independent':
                simulator._channel_update(direction)
            simulator.bpd_x.decode(syndrome[row_boundary:])
        correction_x[shot] = simulator.bpd_x.osdw_decoding
        correction_z[shot] = simulator.bpd_z.osdw_decoding
    if mode == 'no_frame':
        return correction_x, correction_z
    return transport(correction_x, correction_z, case['frame'], case['permutation'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', choices=('strong', 'independent', 'no_frame'), default='strong')
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        correction_x, correction_z = decode(archive, args.mode)
    np.savez_compressed(bootstrap.confined(args.output), correction_x=correction_x,
                        correction_z=correction_z)


if __name__ == '__main__':
    main()
