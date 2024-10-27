import json
import os

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox

# Указываем начальные и конечные координаты (широта, долгота)
start_point = (50.02418570642534, 36.18335487604594)
end_point = (49.8708370386182, 24.02513899243546)

# Настройки OSMnx
ox.config(log_console=True, use_cache=True)

# Используем custom_filter для включения только основных дорог
custom_filter = (
    '["highway"~"motorway|trunk|primary|secondary|tertiary|'
    'motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"]'
)

# Указываем путь к файлу GraphML
graphml_file = "ukraine_graph.graphml"

if os.path.exists(graphml_file):
    G = ox.load_graphml(graphml_file)
else:
    G = ox.graph_from_place(
        "Ukraine", network_type="drive", simplify=True, custom_filter=custom_filter
    )

    ox.save_graphml(G, filepath=graphml_file)

# Находим ближайшие узлы в графе для каждой точки
start_node = ox.nearest_nodes(G, start_point[1], start_point[0])
end_node = ox.nearest_nodes(G, end_point[1], end_point[0])

# Проверяем, есть ли путь между двумя узлами
if nx.has_path(G, start_node, end_node):
    # Находим кратчайший путь между двумя узлами с использованием алгоритма Дейкстры
    shortest_path = nx.shortest_path(G, start_node, end_node, weight="length")

    route_coords = [(G.nodes[node]["y"], G.nodes[node]["x"]) for node in shortest_path]

    route_data = {"route": route_coords}

    with open("shortest_path.json", "w") as f:
        json.dump(route_data, f, indent=4)

    # Визуализируем граф с кратчайшим путём
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
else:
    print("Невозможно проложить маршрут между двумя точками.")
