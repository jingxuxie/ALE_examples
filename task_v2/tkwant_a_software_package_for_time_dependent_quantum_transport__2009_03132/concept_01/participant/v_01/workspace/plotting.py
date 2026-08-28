from PIL import Image, ImageDraw


def plot_lines(series, path, title, xlabel, ylabel):
    image = Image.new('RGB', (960, 600), 'white')
    draw = ImageDraw.Draw(image)
    left, right, top, bottom = 90, 740, 70, 520
    all_x = [value for label, horizontal, vertical in series for value in horizontal]
    all_y = [value for label, horizontal, vertical in series for value in vertical]
    xmin, xmax = min(all_x), max(all_x)
    ymin, ymax = min(all_y), max(all_y)
    if ymax == ymin:
        ymax += 1
    if xmax == xmin:
        xmax += 1
    draw.line((left, top, left, bottom, right, bottom), fill='black', width=2)
    draw.text((left, 25), title, fill='black')
    draw.text((350, 560), xlabel, fill='black')
    draw.text((8, 40), ylabel, fill='black')
    palette = ['#2457a6', '#bc342d', '#158052', '#854dab', '#ad7900', '#177c8a']
    for tick in range(6):
        fraction = tick / 5
        horizontal = left + fraction * (right - left)
        vertical = bottom - fraction * (bottom - top)
        draw.text((horizontal - 15, bottom + 10), f'{xmin + fraction * (xmax - xmin):.3g}', fill='black')
        draw.text((12, vertical), f'{ymin + fraction * (ymax - ymin):.3g}', fill='black')
    for index, (label, horizontal, vertical) in enumerate(series):
        points = [(left + (position - xmin) / (xmax - xmin) * (right - left), bottom - (value - ymin) / (ymax - ymin) * (bottom - top)) for position, value in zip(horizontal, vertical)]
        if len(points) > 1:
            draw.line(points, fill=palette[index % len(palette)], width=2)
        draw.text((760, 80 + 35 * index), label[:26], fill=palette[index % len(palette)])
    image.save(path)
