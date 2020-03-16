from collections import deque, Counter
from enum import Enum
from argparse import ArgumentParser

import png


COMMON_POINTS_SHARE_THRESHOLD = .9
TARGET_POINTS_SHARE = 0.98
Color = Enum('Color', 'BLACK RED')
CHANNEL_MAX = 255
COLOR_THRESHOLD = CHANNEL_MAX // 2


def read_image(path):
    width, height, data, info = png.Reader(path).read()
    image = []
    step = info['planes']
    for row in data:
        row_data = list(row)
        image.append([tuple(row_data[i: i + 3]) for i in range(0, len(row_data), step)])
    return height, width, image


SEARCH_DIRS = [
    (0, -1),
    (0, 1),
    (-1, 0),
    (1, 0)
]


# Компоненты связности выделяются в предположении, что все точки фона имеют один цвет,
# без шума или переходов оттенков.
def extract_component(image, pos, bg_color, height, width, seen):
    component = {pos}
    positions = deque([pos])
    while positions:
        c_x, c_y = positions.popleft()
        seen[c_x][c_y] = True
        for x_d, y_d in SEARCH_DIRS:
            n_x, n_y = c_x + x_d, c_y + y_d
            if 0 <= n_x < height and 0 <= n_y < width and image[n_x][n_y] != bg_color:
                next_pos = n_x, n_y
                if next_pos not in component:
                    component.add(next_pos)
                    positions.append(next_pos)
    return component


def extract_components(image, height, width):
    bg_color = image[0][0]
    seen = [[False] * width for _ in image]
    components = []
    for i in range(height):
        for j in range(width):
            if image[i][j] != bg_color and not seen[i][j]:
                components.append(extract_component(image, (i, j), bg_color, height, width, seen))
    return components


def get_component_center(component):
    xs, ys = [], []
    for x, y in component:
        xs.append(x)
        ys.append(y)
    n = len(component)
    return sum(xs) // n, sum(ys) // n


# Проверяет, является ли компонента свзности прямоугольником.
# Для этого проверяется, что для всех значений первой координаты
# число точек в компоненте связности одинаково.
# Здесь предполагается, что условие параллельности выполняется строго,
# то есть прямоугольнику принадлежат все точки с координатоми из произведения отрезков и только они.
def is_rectangle(component):
    x_hist = Counter(x for x, y in component)
    breadth_hist = Counter(count for value, count in x_hist.items())
    return len(breadth_hist) == 1


def dist(a, b):
    ax, ay = a
    bx, by = b
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** .5


# Проверяет, что компонента связности является кругом. Для этого строится круг с тем же центром,
# и проверяется что он достаточно сильно пересекается с компонентой. Радиус выбирается как квантиль
# расстояния от центра до точки для снижения чувствительности к выбросам.
def is_circle(component):
    center = get_component_center(component)
    dist_counter = Counter(int(dist(center, p)) for p in component)
    target_points = len(component) * TARGET_POINTS_SHARE
    covered_points = 0
    radius = None
    for d, count in sorted(dist_counter.items()):
        covered_points += count
        if covered_points >= target_points:
            radius = d
            break
    cx, cy = center
    circle_points = set()
    for x in range(cx - radius, cx + radius + 1):
        dy = int((radius ** 2 - (x - cx) ** 2) ** .5 + 0.99)
        for y in range(cy - dy, cy + dy + 1):
            circle_points.add((x, y))
    common_points = circle_points & component
    united_points = circle_points | component
    return len(common_points) / len(united_points) >= COMMON_POINTS_SHARE_THRESHOLD


def get_component_color(image, component):
    cx, cy = get_component_center(component)
    cr, cg, cb = image[cx][cy]
    return Color.BLACK if cr < COLOR_THRESHOLD else Color.RED


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('image_path')
    arg_parser.add_argument('--by_circles', action='store_true')
    args = arg_parser.parse_args()

    height, width, image = read_image(args.image_path)
    components = extract_components(image, height, width)

    if args.by_circles:
        circle_components = filter(is_circle, components)
    else:
        circle_components = (c for c in components if not is_rectangle(c))
    color_counter = Counter(get_component_color(image, c) for c in circle_components)
    print(f'{color_counter[Color.RED]} red circle(s) and {color_counter[Color.BLACK]} black circle(s) found')


if __name__ == '__main__':
    main()
