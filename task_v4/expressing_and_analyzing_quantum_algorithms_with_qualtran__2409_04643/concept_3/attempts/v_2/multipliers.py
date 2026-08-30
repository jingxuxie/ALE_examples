from analyze import SUITE, np
from relations import columns, truth_bits, nullspace, monomials

def mobius_bits(vector, cols, width):
    for bit in range(width):
        vector ^= (vector & (cols[0] ^ cols[1 << bit])) << (1 << bit)
    return vector

if __name__ == '__main__':
    for inst in SUITE:
        width = inst['n']
        table = np.array(inst['table'])
        cols = columns(width)
        high_masks = {degree: sum(1 << mask for mask in range(1 << width) if mask.bit_count() > degree) for degree in range(2, width)}
        print(inst['id'], flush=True)
        for bit in range(inst['m']):
            function = truth_bits((table >> bit) & 1)
            relations = []
            for input_degree in (1, 2, 3):
                mons = monomials(width, input_degree)
                vectors = [mobius_bits(cols[mon] & function, cols, width) for mon in mons]
                for output_degree in range(input_degree + 1, width):
                    kernel = nullspace([vector & high_masks[output_degree] for vector in vectors])
                    if kernel:
                        relations.append((input_degree, output_degree, len(kernel)))
                        break
            print(bit, relations, flush=True)
