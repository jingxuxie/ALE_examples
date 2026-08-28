from pathlib import Path

from PIL import Image, ImageDraw


def plot_rows(rows, filename, metric, title):
    image = Image.new('RGB', (1000, 580), 'white')
    drawing = ImageDraw.Draw(image)
    drawing.text((30, 15), title, fill='black')
    values = [float(row[metric]) for row in rows]
    minimum = min(0.0, min(values))
    maximum = max(values) + max(1e-12, max(values) - minimum) * 0.12
    for index, row in enumerate(rows):
        horizontal = 70 + 860 * index / max(1, len(rows) - 1)
        vertical = 490 - 400 * (values[index] - minimum) / (maximum - minimum)
        drawing.line((horizontal, 490, horizontal, vertical), fill='#346ba8', width=6)
        drawing.text((horizontal - 18, max(55, vertical - 20)), '%.3g' % values[index], fill='black')
        drawing.text((horizontal - 18, 505 + (index % 3) * 16), str(index), fill='black')
    drawing.text((35, 555), 'Source: table row order; metric=' + metric, fill='black')
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    image.save(filename)
