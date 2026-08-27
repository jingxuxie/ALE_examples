from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def plot_rows(rows, filename, metric, title):
    height = 130 + 38 * max(1, len(rows))
    image = Image.new('RGB', (1280, height), '#fafbfc')
    drawing = ImageDraw.Draw(image)
    drawing.text((25, 20), title, fill='#152c43')
    if rows:
        values = [float(row[metric]) for row in rows]
        logarithmic = metric == 'distance_to_refined'
        transformed = np.log10(np.maximum(values, 1e-13)) if logarithmic else np.asarray(values)
        minimum = -13 if logarithmic else min(0.0, float(min(transformed)))
        maximum = 0 if logarithmic else max(1e-12, float(max(transformed))) * 1.08
        for index, row in enumerate(rows):
            vertical = 65 + 38 * index
            horizontal = 450 + 640 * (transformed[index] - minimum) / max(1e-12, maximum - minimum)
            color = '#bf5b32' if row.get('configuration') == 'ablation' or row.get('implementation') == 'dense' else '#257a91'
            drawing.text((25, vertical), row['row_id'], fill='#182f44')
            drawing.rectangle((450, vertical, max(451, horizontal), vertical + 14), fill=color)
            drawing.text((1100, vertical), '%.4g' % values[index], fill='#182f44')
        if logarithmic:
            for exponent in [-12, -9, -6, -3, 0]:
                horizontal = 450 + 640 * (exponent - minimum) / (maximum - minimum)
                drawing.text((horizontal - 10, height - 47), '1e%d' % exponent, fill='#465767')
    drawing.text((25, height - 23), 'Regenerated from table rows. Metric: ' + metric + (' (log axis; zero plotted at 1e-13)' if metric == 'distance_to_refined' else ''), fill='#465767')
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    image.save(filename)
