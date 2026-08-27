import numpy as np
from scipy import sparse


def signal(time, spec):
    amplitude = spec['amplitude']
    duration = spec['duration']
    shifted = max(0.0, time - spec.get('start', 0.0))
    fraction = min(1.0, shifted / duration)
    kind = spec['profile']
    if kind == 'ramp':
        return amplitude * (1 - np.cos(np.pi * fraction)) / 2
    if kind == 'voltage_phase':
        if shifted < duration:
            return amplitude * (shifted - duration * np.sin(np.pi * fraction) / np.pi) / 2
        return amplitude * (shifted - duration / 2)
    if kind == 'pulse':
        return amplitude * np.sin(np.pi * fraction) ** 2
    if kind == 'ac':
        return amplitude * (1 - np.cos(np.pi * fraction)) / 2 * np.sin(spec['omega'] * shifted)
    raise ValueError(kind)


def drive_entries(case, interfaces):
    entries = []
    for drive in case['drives']:
        if drive['kind'] == 'contact_phase':
            spec = case['leads'][drive['lead']]
            from .model import decode
            contact = decode(spec['contact'])
            rows, columns = np.nonzero(contact)
            for row, column in zip(rows, columns):
                entries.append((int(row), int(interfaces[drive['lead']][column]), contact[row, column], 'phase', drive))
        else:
            for row, column, real, imag in drive['entries']:
                entries.append((row, column, complex(real, imag), drive['kind'], drive))
    return entries


def perturbation(time, entries, size):
    rows, columns, values = [], [], []
    for row, column, base, kind, spec in entries:
        value = signal(time, spec)
        change = base * (np.exp(-1j * value) - 1) if kind == 'phase' else base * value
        rows.append(row)
        columns.append(column)
        values.append(change)
        if row != column:
            rows.append(column)
            columns.append(row)
            values.append(change.conjugate())
    return sparse.csr_matrix((values, (rows, columns)), shape=(size, size), dtype=complex)
