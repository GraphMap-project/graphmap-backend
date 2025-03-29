import os

import matplotlib.pyplot as plt
import networkx as nx
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


def filter_threats(G, threats):
    G = G.copy()

    threat_nodes = []

    for threat in threats:
        threat_node = ox.nearest_nodes(G, threat[1], threat[0])
        threat_nodes.append(threat_node)

    print(f"--------------------------------{threat_nodes}----------------------------")
    G.remove_nodes_from(threat_nodes)

    return G


CITY_COORDS = {
    "Kyiv": (50.4501, 30.5234),
    "Lviv": (49.8397, 24.0297),
    "Kharkiv": (49.9935, 36.2304),
    "Dnipro": (48.4647, 35.0462),
    "Odesa": (46.4825, 30.7233),
}


def select_landmarks(G):
    """Находит ближайшие узлы к координатам заданных городов."""
    return {
        city: ox.nearest_nodes(G, lon, lat) for city, (lat, lon) in CITY_COORDS.items()
    }


def preprocess_landmarks(G, landmarks):
    """Предварительно вычисляет расстояния от опорных точек до всех узлов."""
    landmark_distances = {}
    for city, node in landmarks.items():
        landmark_distances[city] = nx.single_source_dijkstra_path_length(
            G, node, weight="length"
        )
    return landmark_distances


def alt_heuristic(u, v, landmarks, landmark_distances):
    """Вычисляет ALT-эвристику для A*."""
    return max(
        abs(
            landmark_distances[city].get(u, float("inf"))
            - landmark_distances[city].get(v, float("inf"))
        )
        for city in landmarks
    )
