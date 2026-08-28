import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
COLORS = {'control': '#335b9c', 'vacancy': '#16815d', 'reverse': '#8652a1', 'cluster': '#d36b29'}
FONT = ImageFont.load_default()
RESAMPLING = getattr(Image, 'Resampling', Image)


def rows(path):
    return list(csv.DictReader((ROOT / path).open()))


def text(image, position, content, scale=2, color='#172238', anchor='left'):
    if hasattr(FONT, 'getbbox'):
        bounds = FONT.getbbox(str(content))
    else:
        width, height = FONT.getsize(str(content))
        bounds = (0, 0, width, height)
    layer = Image.new('RGBA', (bounds[2] - bounds[0] + 4, bounds[3] - bounds[1] + 4))
    ImageDraw.Draw(layer).text((2 - bounds[0], 2 - bounds[1]), str(content), font=FONT, fill=color)
    layer = layer.resize((int(layer.width * scale), int(layer.height * scale)), RESAMPLING.LANCZOS)
    horizontal, vertical = position
    if anchor == 'center':
        horizontal -= layer.width // 2
    elif anchor == 'right':
        horizontal -= layer.width
    image.paste(layer, (int(horizontal), int(vertical)), layer)


def panel(image, box, title, series, y_limits=None, x_limits=None, log_y=False, xlabel='time [trap units]'):
    left, top, right, bottom = box
    drawing = ImageDraw.Draw(image)
    text(image, (left, top - 42), title, scale=2)
    values_x = np.concatenate([np.asarray(item[1], dtype=float) for item in series])
    values_y = np.concatenate([np.asarray(item[2], dtype=float) for item in series])
    if log_y:
        values_y = np.log10(np.maximum(values_y, 1e-16))
    minimum_x, maximum_x = x_limits or (float(values_x.min()), float(values_x.max()))
    minimum_y, maximum_y = y_limits or (float(values_y.min()), float(values_y.max()))
    if not y_limits:
        span = maximum_y - minimum_y
        minimum_y -= 0.08 * (span or 1)
        maximum_y += 0.08 * (span or 1)
    maximum_x = max(maximum_x, minimum_x + 1e-12)
    maximum_y = max(maximum_y, minimum_y + 1e-12)
    for fraction in np.linspace(0, 1, 5):
        pixel_y = bottom - fraction * (bottom - top)
        drawing.line([(left, pixel_y), (right, pixel_y)], fill='#dce2e9', width=1)
        value = minimum_y + fraction * (maximum_y - minimum_y)
        label = f'1e{value:.1f}' if log_y else f'{value:.3g}'
        text(image, (left - 12, pixel_y - 12), label, scale=1.6, anchor='right')
    for fraction in np.linspace(0, 1, 4):
        pixel_x = left + fraction * (right - left)
        drawing.line([(pixel_x, top), (pixel_x, bottom)], fill='#edf0f4', width=1)
        text(image, (pixel_x, bottom + 9), f'{minimum_x + fraction * (maximum_x - minimum_x):.3g}', scale=1.6, anchor='center')
    drawing.line([(left, top), (left, bottom), (right, bottom)], fill='#5e6b7b', width=2)
    for label, coordinates_x, coordinates_y, color in series:
        coordinates_y = np.asarray(coordinates_y, dtype=float)
        if log_y:
            coordinates_y = np.log10(np.maximum(coordinates_y, 1e-16))
        points = [(left + (horizontal - minimum_x) / (maximum_x - minimum_x) * (right - left),
                   bottom - (vertical - minimum_y) / (maximum_y - minimum_y) * (bottom - top))
                  for horizontal, vertical in zip(coordinates_x, coordinates_y)]
        if len(points) > 1:
            drawing.line(points, fill=color, width=3)
        for horizontal, vertical in points:
            drawing.ellipse((horizontal - 4, vertical - 4, horizontal + 4, vertical + 4), fill=color)
    text(image, ((left + right) / 2, bottom + 43), xlabel, scale=1.7, anchor='center')


def legend(image, entries, position=(100, 77), spacing=305):
    drawing = ImageDraw.Draw(image)
    for index, (name, color) in enumerate(entries):
        horizontal = position[0] + spacing * index
        drawing.line((horizontal, position[1] + 12, horizontal + 28, position[1] + 12), fill=color, width=5)
        text(image, (horizontal + 35, position[1]), name, scale=1.8)


def plot_primary():
    data = rows('results.csv')
    image = Image.new('RGB', (1440, 1100), '#ffffff')
    text(image, (65, 20), 'Conservative phase engineering: bulk order and sound', scale=2.7)
    legend(image, list(COLORS.items()))
    specifications = [('g6_near', 'g6: separation [0, 2.8)', (-0.05, 1.05)),
                      ('g6_far', 'g6: separation [5.6, 20)', (-0.05, 1.05)),
                      ('defect_radius', 'Non-sixfold defect RMS radius', (0, 4.5)),
                      ('Ec', 'Compressible kinetic energy Ec', (0, 0.85))]
    for index, (column, title, limits) in enumerate(specifications):
        horizontal = 115 + (index % 2) * 700
        vertical = 175 + (index // 2) * 445
        series = []
        for case, color in COLORS.items():
            selected = [row for row in data if row['case'] == case]
            series.append((case, [float(row['time']) for row in selected], [float(row[column]) for row in selected], color))
        panel(image, (horizontal, vertical, horizontal + 550, vertical + 320), title, series, y_limits=limits)
    text(image, (65, 1060), 'Source: results.csv. Lines join saved frames; no claim about unsampled extrema.', scale=1.7)
    image.save(ROOT / 'figures/primary_result.png')


def plot_robustness():
    convergence = rows('convergence.csv')
    scaling = rows('scaling.csv')
    image = Image.new('RGB', (1440, 1060), '#ffffff')
    text(image, (65, 20), 'Temporal refinement, alternative method, and measured cost', scale=2.5)
    legend(image, list(COLORS.items()))
    series = []
    for case, color in COLORS.items():
        selected = [row for row in convergence if row['case'] == case and float(row['time']) > 0]
        series.append((case, [float(row['time']) for row in selected], [float(row['wave_l2']) for row in selected], color))
    panel(image, (115, 175, 665, 455), 'Primary vs refinement: wave L2', series, log_y=True)
    primary = rows('results.csv')
    alternative = rows('ablation.csv')
    series = []
    for case, color in COLORS.items():
        first = [row for row in primary if row['case'] == case]
        second = [row for row in alternative if row['case'] == case]
        series.append((case, [float(row['time']) for row in first],
                       [abs(float(left['g6_far']) - float(right['g6_far'])) for left, right in zip(first, second)], color))
    panel(image, (815, 175, 1365, 455), 'Absolute g6_far change: ablation', series)
    for index, (column, title, divisor) in enumerate([('wall_seconds', 'Campaign wall time [s]', 1),
                                                     ('max_rss_kib', 'Process peak RSS [MiB]', 1024)]):
        left, top, right, bottom = 115 + index * 700, 650, 665 + index * 700, 930
        values = []
        variants = ['primary', 'ablation', 'refinement']
        for variant in variants:
            selected = [float(row[column]) for row in scaling if row['variant'] == variant]
            values.append((sum(selected) if column == 'wall_seconds' else max(selected)) / divisor)
        panel(image, (left, top, right, bottom), title,
              [('cost', [0, 1, 2], values, '#466c95')], y_limits=(0, max(values) * 1.2), x_limits=(-0.4, 2.4), xlabel='')
        drawing = ImageDraw.Draw(image)
        for variant_index, (variant, value) in enumerate(zip(variants, values)):
            center = left + (variant_index + 0.4) / 2.8 * (right - left)
            height = value / (max(values) * 1.2) * (bottom - top)
            drawing.rectangle((center - 48, bottom - height, center + 48, bottom), fill='#91abc8', outline='#466c95')
            text(image, (center, bottom - height - 32), f'{value:.2f}', scale=1.7, anchor='center')
            drawing.rectangle((center - 58, bottom + 4, center + 58, bottom + 38), fill='white')
            text(image, (center, bottom + 10), variant, scale=1.5, anchor='center')
    text(image, (65, 1018), 'Sources: convergence.csv, results.csv, ablation.csv, scaling.csv. Timings include diagnostics and I/O.', scale=1.7)
    image.save(ROOT / 'figures/robustness_or_scaling.png')


def plot_healing():
    physics = rows('experiments/calibration_primary/results.csv')
    baseline = rows('experiments/baseline/calibration/results.csv')
    healing = rows('healing.csv')
    old_healing = rows('baseline_healing.csv')
    times = [float(row['time']) for row in physics]
    image = Image.new('RGB', (1440, 650), 'white')
    text(image, (65, 22), 'Isolated erasure: density heals; sound is not a vortex', scale=2.5)
    legend(image, [('repaired', '#16815d'), ('baseline', '#c45146')], spacing=260)
    panel(image, (110, 170, 690, 485), 'Mean density inside r < 0.35',
          [('repaired', times, [float(row['core_mean_density']) for row in healing], '#16815d'),
           ('baseline', times, [float(row['core_mean_density']) for row in old_healing], '#c45146')])
    panel(image, (820, 170, 1365, 485), 'Unnormalized second moment r2',
          [('repaired', times, [float(row['r2']) for row in physics], '#16815d'),
           ('baseline', times, [float(row['r2']) for row in baseline], '#c45146')])
    text(image, (65, 595), 'Sources: healing.csv, baseline_healing.csv, and calibration results tables. No density edit at t=0.', scale=1.7)
    image.save(ROOT / 'figures/calibration_healing.png')


def plot_density():
    asset = np.load(ROOT / 'inputs/lattice_state.npz')
    axis_x, axis_y = asset['x'], asset['y']
    columns = np.flatnonzero((axis_x >= -7) & (axis_x <= 7))
    rows_y = np.flatnonzero((axis_y >= -7) & (axis_y <= 7))
    image = Image.new('RGB', (1470, 1270), 'white')
    text(image, (45, 15), 'Density and signed phase cores; common density scale', scale=2.5)
    tables = {(row['case'], int(row['frame'])): row for row in rows('results.csv')}
    for row_index, case in enumerate(COLORS):
        frames = np.load(ROOT / 'experiments/primary' / (case + '.npz'))['psi']
        diagnostics = json.loads((ROOT / 'experiments/primary' / (case + '.json')).read_text())
        for column_index, frame in enumerate((0, 2, 4)):
            density = abs(frames[frame][np.ix_(rows_y, columns)]) ** 2
            brightness = np.clip(density[::-1] / 0.011, 0, 1)
            colors = np.stack((255 * brightness, 245 * brightness ** 0.7, 50 + 160 * (1 - brightness)), axis=-1).astype('uint8')
            picture = Image.fromarray(colors).resize((265, 265), RESAMPLING.BILINEAR)
            horizontal = 130 + column_index * 475
            vertical = 80 + row_index * 290
            image.paste(picture, (horizontal, vertical))
            drawing = ImageDraw.Draw(image)
            for position_x, position_y, charge in diagnostics[frame]['cores']:
                if -7 <= position_x <= 7 and -7 <= position_y <= 7:
                    pixel_x = horizontal + (position_x - axis_x[columns[0]]) / (axis_x[columns[-1]] - axis_x[columns[0]]) * 264
                    pixel_y = vertical + (axis_y[rows_y[-1]] - position_y) / (axis_y[rows_y[-1]] - axis_y[rows_y[0]]) * 264
                    color = '#cf1338' if charge > 0 else '#00eeee'
                    drawing.ellipse((pixel_x - 3, pixel_y - 3, pixel_x + 3, pixel_y + 3), outline=color, width=2)
            row = tables[case, frame]
            text(image, (horizontal + 275, vertical + 40), f't={row["time"]}', scale=1.5)
            text(image, (horizontal + 275, vertical + 75), f'g6={float(row["g6_far"]):.3f}', scale=1.5)
            text(image, (horizontal + 275, vertical + 110), f'N+={row["nplus"]}', scale=1.5)
            text(image, (horizontal + 275, vertical + 145), f'N-={row["nminus"]}', scale=1.5)
        text(image, (8, 175 + row_index * 290), case, scale=1.7, color=COLORS[case])
    text(image, (45, 1240), 'Fields: experiments/primary/*.npz; cores: *.json. Red positive, cyan negative. Window [-7,7] x [-7,7].', scale=1.5)
    image.save(ROOT / 'figures/density_snapshots.png')


if __name__ == '__main__':
    (ROOT / 'figures').mkdir(exist_ok=True)
    plot_primary()
    plot_robustness()
    plot_healing()
    plot_density()
