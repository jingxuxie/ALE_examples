import unittest

import numpy as np

from probe import coding_rows


class CodingTests(unittest.TestCase):
    def test_linear_encoder_and_padding(self):
        generator = np.random.default_rng(428178)
        for degree, strength in ((8, 6), (9, 20), (9, 30)):
            decoder, offsets, active = coding_rows(200, degree, strength)
            for trial in range(64):
                bits = generator.integers(0, 2, 200, dtype=np.uint8)
                encoded = decoder.encode(np.packbits(bits).tobytes())
                parity = np.unpackbits(np.frombuffer(encoded, dtype=np.uint8))
                np.testing.assert_array_equal(parity[active], (offsets[201:] @ bits) & 1)
                inactive = np.setdiff1d(np.arange(len(parity)), active)
                np.testing.assert_array_equal(parity[inactive], 0)

    def test_bounded_distance_correction(self):
        generator = np.random.default_rng(781132)
        for degree, strength in ((8, 6), (9, 20), (9, 30)):
            decoder, offsets, active = coding_rows(200, degree, strength)
            for trial in range(64):
                bits = generator.integers(0, 2, 200, dtype=np.uint8)
                codeword = ((offsets[1:] @ bits) & 1).astype(np.uint8)
                error_count = trial % (strength + 1)
                flips = generator.choice(len(codeword), error_count, replace=False)
                codeword[flips] ^= 1
                message = bytearray(np.packbits(codeword[:200]).tobytes())
                parity = np.zeros(decoder.ecc_bytes * 8, dtype=np.uint8)
                parity[active] = codeword[200:]
                parity = bytearray(np.packbits(parity).tobytes())
                self.assertEqual(decoder.decode(message, parity), error_count)
                decoder.correct(message, parity)
                np.testing.assert_array_equal(np.unpackbits(np.frombuffer(message, dtype=np.uint8)), bits)


if __name__ == "__main__":
    unittest.main()
