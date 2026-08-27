import csv
from pathlib import Path

from PIL import Image, ImageDraw


def plot_results(records, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    sources = []
    palette = ['#1f77b4', '#d62728', '#2ca02c', '#9467bd', '#ff7f0e']
    for filename, quantity in [('primary_result.png', 'gap'), ('robustness_or_scaling.png', 'energy')]:
        image = Image.new('RGB', (1100, 800), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((35, 15), f'{quantity} versus free-energy cutoff; line = configuration', fill='black')
        for panel, case in enumerate(dict.fromkeys(row['case'] for row in records)):
            candidates = [row for row in records if row['case'] == case and row['method'] == 'production']
            if quantity == 'energy':
                example = min(candidates, key=lambda row: row['energy'])
            else:
                example = min((row for row in candidates if row['gap'] > 1e-9), key=lambda row: row['gap'])
            selected = [row for row in records if row['case'] == case and row['sector'] == example['sector']
                        and row['level'] == example['level']]
            if not selected:
                continue
            sector = example['sector']
            left, top = 40 + (panel % 3) * 360, 70 + (panel // 3) * 360
            draw.text((left, top - 22), f'{case} / {sector}', fill='black')
            draw.line((left, top, left, top + 230, left + 290, top + 230), fill='black', width=2)
            minimum_x, maximum_x = min(row['cutoff'] for row in selected), max(row['cutoff'] for row in selected)
            minimum_y, maximum_y = min(row[quantity] for row in selected), max(row[quantity] for row in selected)
            draw.text((left + 5, top + 235), f'{minimum_x:g}', fill='black')
            draw.text((left + 255, top + 235), f'{maximum_x:g}', fill='black')
            draw.text((left + 115, top + 235), 'cutoff', fill='black')
            for method_index, method in enumerate(dict.fromkeys(row['method'] for row in selected)):
                points = []
                for row in sorted((row for row in selected if row['method'] == method), key=lambda item: item['cutoff']):
                    horizontal = left + 10 + 270 * (row['cutoff'] - minimum_x) / max(maximum_x - minimum_x, 1e-8)
                    vertical = top + 220 - 210 * (row[quantity] - minimum_y) / max(maximum_y - minimum_y, 1e-8)
                    points.append((horizontal, vertical))
                    draw.ellipse((horizontal - 2, vertical - 2, horizontal + 2, vertical + 2), fill=palette[method_index % len(palette)])
                    sources.append({'figure': filename, 'row_id': row['row_id'], 'x_quantity': 'cutoff',
                                    'y_quantity': quantity, 'x': row['cutoff'], 'y': row[quantity]})
                if len(points) > 1:
                    draw.line(points, fill=palette[method_index % len(palette)], width=2)
                draw.text((left + 10, top + 260 + method_index * 13), method, fill=palette[method_index % len(palette)])
            draw.text((left + 3, top + 5), f'{maximum_y:.5g}', fill='black')
            draw.text((left + 3, top + 205), f'{minimum_y:.5g}', fill='black')
        image.save(destination / filename)
    with (destination / 'source.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['figure', 'row_id', 'x_quantity', 'y_quantity', 'x', 'y'])
        writer.writeheader()
        writer.writerows(sources)
