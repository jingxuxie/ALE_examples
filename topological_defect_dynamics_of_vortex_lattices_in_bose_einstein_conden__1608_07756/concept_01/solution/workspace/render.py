import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def panel(draw, bounds, title, series, xlabel, ylabel):
    left, top, right, bottom = bounds
    draw.text((left, top - 25), title, fill='black')
    draw.line((left, top, left, bottom, right, bottom), fill='black', width=2)
    values_x = [value for label, times, values in series for value in times]
    values_y = [value for label, times, values in series for value in values]
    minimum_x, maximum_x = min(values_x), max(values_x)
    minimum_y, maximum_y = min(0, min(values_y)), max(values_y)
    if maximum_y <= minimum_y:
        maximum_y = minimum_y + 1
    colors = ['#1565c0', '#d84315', '#388e3c', '#7b1fa2', '#455a64']
    for index, (label, times, values) in enumerate(series):
        points = [(left + (right - left) * (time - minimum_x) / max(maximum_x - minimum_x, 1e-9), bottom - (bottom - top) * (value - minimum_y) / (maximum_y - minimum_y)) for time, value in zip(times, values)]
        if len(points) > 1:
            draw.line(points, fill=colors[index % len(colors)], width=3)
        for position_x, position_y in points:
            draw.ellipse((position_x - 3, position_y - 3, position_x + 3, position_y + 3), fill=colors[index % len(colors)])
        draw.text((left + 10, top + 14 * index), label, fill=colors[index % len(colors)])
    for fraction in [0, 0.5, 1]:
        coordinate = bottom - fraction * (bottom - top)
        draw.text((left - 42, coordinate - 5), f'{minimum_y + fraction * (maximum_y - minimum_y):.2g}', fill='black')
        draw.text((left + fraction * (right - left) - 10, bottom + 5), f'{minimum_x + fraction * (maximum_x - minimum_x):.2g}', fill='black')
    draw.text(((left + right) / 2 - 25, bottom + 23), xlabel, fill='black')
    draw.text((left, top - 12), ylabel, fill='black')


def read(path):
    return list(csv.DictReader(open(path)))


def render(root):
    root = Path(root)
    (root / 'figures').mkdir(exist_ok=True)
    rows = read(root / 'results.csv')
    image = Image.new('RGB', (1100, 520), 'white')
    draw = ImageDraw.Draw(image)
    for column, title, offset in [('g6_far', 'Long-range bond orientation', 0), ('defect_radius', 'Spatial extent of non-sixfold bulk cores', 550)]:
        series = []
        for case in sorted(set(row['case'] for row in rows)):
            selected = [row for row in rows if row['case'] == case]
            series.append((case, [float(row['time']) for row in selected], [float(row[column]) for row in selected]))
        panel(draw, (65 + offset, 70, 515 + offset, 420), title, series, 'time', column)
    image.save(root / 'figures/primary_result.png')
    image = Image.new('RGB', (1100, 520), 'white')
    draw = ImageDraw.Draw(image)
    variants = [('primary', rows), ('crop ablation', read(root / 'ablation.csv')), ('half timestep', read(root / 'experiments/refinement/results.csv'))]
    series = []
    for label, data in variants:
        selected = [row for row in data if row['case'] == 'vacancy']
        series.append((label, [float(row['time']) for row in selected], [float(row['n5']) + float(row['n7']) for row in selected]))
    panel(draw, (65, 70, 515, 420), 'Vacancy coordination: guard-region ablation', series, 'time', 'N5 + N7')
    scales = read(root / 'scaling.csv')
    series = []
    for variant in ['primary', 'ablation', 'refinement']:
        selected = [row for row in scales if row['variant'] == variant]
        series.append((variant, list(range(len(selected))), [float(row['wall_seconds']) for row in selected]))
    panel(draw, (615, 70, 1065, 420), 'Measured end-to-end cost per experiment', series, 'case index', 'wall seconds')
    image.save(root / 'figures/robustness_or_scaling.png')


if __name__ == '__main__':
    import sys
    render(sys.argv[1])
