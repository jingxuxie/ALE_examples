import csv
import math
import struct
import zlib
from pathlib import Path


def chunk(label, data):
    return struct.pack("!I", len(data)) + label + data + struct.pack("!I", zlib.crc32(label + data) & 0xffffffff)


def plot_rows(rows, destination, horizontal, vertical):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.with_suffix(".csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    width, height = 800, 480
    pixels = bytearray([255] * (width * height * 3))

    def point(column, row, color):
        if 0 <= column < width and 0 <= row < height:
            position = (row * width + column) * 3
            pixels[position:position + 3] = bytes(color)

    def line(first, second, color):
        count = max(abs(second[0] - first[0]), abs(second[1] - first[1]), 1)
        for index in range(count + 1):
            fraction = index / count
            point(round(first[0] + fraction * (second[0] - first[0])),
                  round(first[1] + fraction * (second[1] - first[1])), color)

    line((65, 30), (65, 430), (40, 40, 40))
    line((65, 430), (765, 430), (40, 40, 40))
    transformed = [(math.log10(max(float(row[horizontal]), 1e-18)),
                    math.log10(max(float(row[vertical]), 1e-18))) for row in rows]
    left = min(value[0] for value in transformed)
    right = max(value[0] for value in transformed)
    bottom = min(value[1] for value in transformed)
    top = max(value[1] for value in transformed)
    previous = {}
    palette = [(30, 80, 180), (200, 65, 40), (40, 145, 75), (160, 60, 180)]
    groups = {}
    for row, pair in zip(rows, transformed):
        group = row.get("profile", "production")
        if group not in groups:
            groups[group] = palette[len(groups) % len(palette)]
        coordinate = (round(65 + 700 * (pair[0] - left) / max(right - left, 1e-9)),
                      round(430 - 400 * (pair[1] - bottom) / max(top - bottom, 1e-9)))
        if group in previous:
            line(previous[group], coordinate, groups[group])
        for delta_column in range(-3, 4):
            for delta_row in range(-3, 4):
                point(coordinate[0] + delta_column, coordinate[1] + delta_row, groups[group])
        previous[group] = coordinate
    raw = b"".join(b"\x00" + pixels[row * width * 3:(row + 1) * width * 3] for row in range(height))
    metadata = f"Axes: log10({horizontal}), log10({vertical}); groups: {groups}; source: {destination.with_suffix('.csv').name}"
    content = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0))
    content += chunk(b"tEXt", b"Description\0" + metadata.encode())
    content += chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    destination.write_bytes(content)
