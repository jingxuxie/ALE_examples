import struct

import numpy as np

INPUT_MAGIC = b'ERAD3B2\0'
OUTPUT_MAGIC = b'ERAD3O2\0'
EVENT = np.dtype([('momenta', '<f8', (5, 4)), ('labels', '<i4', (5,)),
                  ('slots', '<i4', (3,)), ('axis', '<f8', (4,))])


def serialize(cases):
    events = np.empty(len(cases), dtype=EVENT)
    for index, case in enumerate(cases):
        events[index] = (case['p'], case['labels'], case['slots'], case['axis'])
    return INPUT_MAGIC + struct.pack('<I', len(cases)) + events.tobytes()


def decode(payload, count):
    if len(payload) != 12 + count * 84 * 8:
        raise ValueError('Binary output byte count mismatch; no trailer or extra records permitted')
    if payload[:8] != OUTPUT_MAGIC or struct.unpack_from('<I', payload, 8)[0] != count:
        raise ValueError('Binary output magic or event count mismatch')
    return np.frombuffer(payload, dtype='<f8', offset=12).reshape(count, 84)
