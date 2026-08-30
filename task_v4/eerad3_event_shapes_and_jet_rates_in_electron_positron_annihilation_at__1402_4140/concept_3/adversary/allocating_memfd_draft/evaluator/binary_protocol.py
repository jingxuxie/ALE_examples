import struct

import numpy as np

INPUT_MAGIC = b'ERAD3B3\0'
OUTPUT_MAGIC = b'ERAD3O3\0'


def serialize(cases):
    buffers = [np.asarray([case[name] for case in cases], dtype=dtype).tobytes()
               for name, dtype in [('p', '<f8'), ('labels', '<i4'), ('slots', '<i4'), ('axis', '<f8')]]
    return INPUT_MAGIC + struct.pack('<I', len(cases)) + b''.join(buffers)


def decode(payload, count):
    if len(payload) != 12 + count * 84 * 8:
        raise ValueError('Binary output byte count mismatch; no trailer or extra records permitted')
    if payload[:8] != OUTPUT_MAGIC or struct.unpack_from('<I', payload, 8)[0] != count:
        raise ValueError('Binary output magic or event count mismatch')
    return np.frombuffer(payload, dtype='<f8', offset=12).reshape(count, 84)
