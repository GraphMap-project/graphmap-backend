import os
import pickle
import time
import uuid

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from geopy.geocoders import Nominatim
from scipy.spatial.distance import euclidean
from shapely.geometry import LineString, Point, Polygon


def load_graph(pkl_file, custom_filter):
    if os.path.exists(f"{pkl_file}.pkl"):
        with open(f"{pkl_file}.pkl", "rb") as f:
            G = pickle.load(f)
            print("Graph loaded from .pkl file.")
    elif os.path.exists(f"{pkl_file}.graphml"):
        print("Found .graphml file, loading and converting to .pkl...")
        G = ox.load_graphml("ukraine_graph.graphml")
        with open(f"{pkl_file}.pkl", "wb") as f:
            pickle.dump(G, f)
            print("Graph saved to .pkl file from .graphml.")
    else:
        G = ox.graph_from_place(
            "Ukraine", network_type="drive", simplify=True, custom_filter=custom_filter
        )
        with open(f"{pkl_file}.pkl", "wb") as f:
            pickle.dump(G, f)
            print("Graph created and saved to .pkl file.")
    return G


def extract_edge_geometries(G, path):
    edge_lines = []

    for u, v in zip(path[:-1], path[1:]):
        data = G.get_edge_data(u, v)

        # Если несколько рёбер между u и v
        if isinstance(data, dict):
            edge_data = data[list(data.keys())[0]]
        else:
            edge_data = data

        # Если есть геометрия ребра — используем её
        if "geometry" in edge_data:
            line = edge_data["geometry"]
            edge_lines.append(line)
        else:
            # Иначе просто соединяем две точки прямой
            point_u = (G.nodes[u]["x"], G.nodes[u]["y"])
            point_v = (G.nodes[v]["x"], G.nodes[v]["y"])
            line = LineString([point_u, point_v])
            edge_lines.append(line)

    # Объединяем все линии в одну последовательность координат
    coords = []
    for line in edge_lines:
        coords.extend(list(line.coords))

    # Убедимся, что это формат [lat, lng], а не [lng, lat]
    return [(lat, lon) for lon, lat in coords]


def plot_shortest_path(G, full_route, points, start_point, end_point):
    fig, ax = ox.plot_graph_route(
        G,
        full_route,
        route_linewidth=4,  # Толщина линии пути
        node_size=0,  # Отключаем узлы
        bgcolor="w",  # Цвет фона
        route_color="r",  # Цвет маршрута
        route_alpha=0.7,  # Прозрачность маршрута
        show=False,  # Не показываем график
        close=False,  # Не закрывать окно
    )

    # Координаты всех точек (для визуализации на карте)
    lons = [point[1] for point in points]  # Долготы (X)
    lats = [point[0] for point in points]  # Широты (Y)

    # Добавляем точки маршрута (зелёные маркеры)
    ax.scatter(
        start_point[1],
        start_point[0],
        c="g",  # Цвет маркеров
        s=100,  # Размер маркеров
        zorder=5,  # Порядок наложения
        label="Route Points",
    )

    ax.scatter(
        end_point[1],
        end_point[0],
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

    polygons = [Polygon([(lng, lat) for lat, lng in threat]) for threat in threats]

    nodes_to_remove = []

    for node, data in G.nodes(data=True):
        point = Point(data["x"], data["y"])  # x = lon, y = lat

        # Проверим, находится ли узел внутри хотя бы одного полигона
        if any(polygon.contains(point) for polygon in polygons):
            nodes_to_remove.append(node)

    print(f"Deleting {len(nodes_to_remove)} nodes")
    G.remove_nodes_from(nodes_to_remove)

    return G


def auto_select_landmarks(G, start_node, end_node, num_landmarks=5):
    """
    Automatically selects landmarks for ALT algorithm based on the distance between
    start and end points, with random offsets added.

    Args:
        G: NetworkX graph
        start_node: Starting node ID
        end_node: Ending node ID
        num_landmarks: Number of landmarks to select

    Returns:
        Dictionary mapping landmark names to node IDs
    """

    # Get coordinates of start and end nodes
    start_coords = (G.nodes[start_node]["y"], G.nodes[start_node]["x"])
    end_coords = (G.nodes[end_node]["y"], G.nodes[end_node]["x"])

    # Calculate coordinates for each landmark
    landmarks = {}
    for i in range(1, num_landmarks + 1):
        # Interpolate between start and end
        t = i / (num_landmarks + 2)
        base_lat = start_coords[0] + t * (end_coords[0] - start_coords[0])
        base_lon = start_coords[1] + t * (end_coords[1] - start_coords[1])

        # Add random offset between -2 and 2 to both coordinates
        random_lat_offset = np.random.uniform(-2, 2)
        random_lon_offset = np.random.uniform(-2, 2)

        lat = base_lat + random_lat_offset
        lon = base_lon + random_lon_offset

        # Find nearest node to this point
        node = ox.nearest_nodes(G, lon, lat)
        landmarks[f"landmark_{i}"] = node
        print(f"landmark_{i} = {G.nodes[node]['y']}, {G.nodes[node]['x']}")

    return landmarks


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


def get_settlements_along_route(G, route_nodes, sample_interval=10):
    """Extracts settlements names along route"""
    print("Extracting settlements along route...")

    settlements = []
    current_settlement = None

    # Geolocator - будет искать инфу по координатам
    geolocator = Nominatim(user_agent="route_planner")

    # берем часть узлов (не все)
    sampled_nodes = [
        route_nodes[i] for i in range(0, len(route_nodes), sample_interval)
    ]

    for node in sampled_nodes:
        lat = G.nodes[node]["y"]
        lon = G.nodes[node]["x"]

        try:
            # Получаем по координатам инфу
            location = geolocator.reverse(f"{lat}, {lon}", language="uk")

            if location and location.raw.get("address"):
                # Пытаемся получить название населенного пункта
                address = location.raw["address"]

                # Приоритет полей для населенных пунктов
                for field in [
                    "city",
                    "town",
                    "village",
                    "hamlet",
                    "suburb",
                    "district",
                    "municipality",
                ]:
                    if field in address:
                        settlement_name = address[field]

                        # Добавляем только если это новый населенный пункт
                        if settlement_name != current_settlement:
                            settlements.append(settlement_name)
                            current_settlement = settlement_name
                        break

            # Делаем паузу между запросами, чтобы не превышать лимиты API
            time.sleep(1)

        except Exception as e:
            # Пропускаем ошибки геокодирования
            continue
    return settlements


def save_route_to_file(route_coords, settlements, total_distance):
    """Save route to txt file"""
    print("Saving route to file...")

    unique_id = str(uuid.uuid4())

    filename = f"route_{unique_id}.txt"
    file_path = os.path.join("temp_files", filename)

    os.makedirs("temp_files", exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Інформація про маршрут\n")
        f.write(f"Відстань: {round(total_distance / 1000, 2)} км\n")

        f.write("\nТочки маршруту:\n")
        if settlements:
            for i, settlement in enumerate(settlements, 1):
                f.write(f"{i}. {settlement}\n")
        else:
            f.write("Немає інформації про міста\n")

        f.write("\nКоординати точок маршруту:\n")
        for i, coord in enumerate(route_coords, 1):
            f.write(f"{i}. [{coord[1]}, {coord[0]}]\n")

    return filename
