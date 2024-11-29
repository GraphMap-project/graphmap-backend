import os

import matplotlib.pyplot as plt
import osmnx as ox


def load_graph(graphml_file, custom_filter):
    if os.path.exists(graphml_file):
        G = ox.load_graphml(graphml_file)
    else:
        G = ox.graph_from_place(
            "Ukraine", network_type="drive", simplify=True, custom_filter=custom_filter
        )
        ox.save_graphml(G, filepath=graphml_file)
    return G


def build_shortest_path(G, shortest_path, start_point, end_point):
    fig, ax = ox.plot_graph_route(
        G,
        shortest_path,
        route_linewidth=4,  # Толщина линии пути
        node_size=0,  # Отключаем узлы
        bgcolor="w",  # Цвет фона
        route_color="r",  # Цвет маршрута
        route_alpha=0.7,  # Прозрачность маршрута
    )

    # Добавляем начальную и конечную точки как зелёные круги
    ax.scatter(
        [start_point[1], end_point[1]],  # Долгота (X)
        [start_point[0], end_point[0]],  # Широта (Y)
        c="g",  # Цвет маркеров
        s=100,  # Размер маркеров
        zorder=5,  # Порядок наложения (над графом)
        label="Start/End Points",
    )
    plt.show()


def build_shortest_path2(G, full_route, points):
    fig, ax = ox.plot_graph_route(
        G,
        full_route,
        route_linewidth=4,  # Толщина линии пути
        node_size=0,  # Отключаем узлы
        bgcolor="w",  # Цвет фона
        route_color="r",  # Цвет маршрута
        route_alpha=0.7,  # Прозрачность маршрута
    )

    # Координаты всех точек (для визуализации на карте)
    lons = [point[1] for point in points]  # Долготы (X)
    lats = [point[0] for point in points]  # Широты (Y)

    # Добавляем точки маршрута (зелёные маркеры)
    ax.scatter(
        lons,
        lats,
        c="g",  # Цвет маркеров
        s=100,  # Размер маркеров
        zorder=5,  # Порядок наложения
        label="Route Points",
    )

    # Показываем легенду
    ax.legend()
    plt.show()
