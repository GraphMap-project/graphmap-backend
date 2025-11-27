import os
import pickle

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import LineString, Point, Polygon
from sqlmodel import Session

from config.database import engine
from utils.db_utils import find_nearest_settlement


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


def plot_shortest_path(
    G,
    full_route,
    points,
    start_point,
    end_point,
    intermediate_points=None,
    landmarks=None,
    threats=None,
):
    fig, ax = ox.plot_graph_route(
        G,
        full_route,
        route_linewidth=4,
        node_size=0,
        bgcolor="w",
        route_color="r",
        route_alpha=0.7,
        show=False,
        close=False,
    )

    # 1. Plot Start & End Points (Green)
    # Note: ax.scatter expects (x, y) which corresponds to (Longitude, Latitude)
    ax.scatter(
        start_point[1], start_point[0], c="g", s=100, zorder=5, label="Start Point"
    )
    ax.scatter(end_point[1], end_point[0], c="g", s=100, zorder=5, label="End Point")

    # 2. Plot Intermediate Points (Orange) - NEW
    if intermediate_points:
        int_lons = [p[1] for p in intermediate_points]
        int_lats = [p[0] for p in intermediate_points]
        ax.scatter(
            int_lons,
            int_lats,
            c="orange",
            s=80,
            zorder=5,
            marker="o",
            label="Intermediate Points",
        )

    # 3. Plot Landmarks (Blue Stars)
    if landmarks:
        landmark_coords = [(G.nodes[l]["y"], G.nodes[l]["x"]) for l in landmarks]
        landmark_lats = [lat for lat, lon in landmark_coords]
        landmark_lons = [lon for lat, lon in landmark_coords]

        ax.scatter(
            landmark_lons,
            landmark_lats,
            c="blue",
            marker="*",
            s=120,
            zorder=6,
            label="Landmarks",
        )

    # 4. Plot Threats (Red Zones/Lines) - NEW
    if threats:
        for i, threat in enumerate(threats):
            # Safety check: ensure threat is not empty
            if not threat:
                continue

            # Handle the specific list structure you provided
            # We assume 'threat' is a list of [lat, lon] points.
            # Matplotlib requires (x, y) which is (lon, lat).

            try:
                # Swap [lat, lon] -> (lon, lat)
                coord_sequence = [(p[1], p[0]) for p in threat]

                # Create the polygon patch
                poly_patch = MplPolygon(
                    coord_sequence,
                    closed=True,  # Automatically close the shape
                    edgecolor="red",
                    facecolor="red",
                    alpha=0.3,  # Semi-transparent to see roads underneath
                    zorder=4,
                    label="Threat Area" if i == 0 else "",  # Label only the first one
                )
                ax.add_patch(poly_patch)
            except (IndexError, TypeError):
                print(f"Skipping malformed threat at index {i}: {threat}")

    ax.legend(loc="upper right")
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


def alt_heuristic(u, v, landmarks, landmark_distances):
    estimates = []
    for landmark in landmarks:
        dist_u = landmark_distances[landmark].get(u, 0)
        dist_v = landmark_distances[landmark].get(v, 0)
        estimates.append(abs(dist_u - dist_v))
    return max(estimates) if estimates else 0


async def get_settlements_along_route(G, route_nodes, sample_interval=10):
    """Extracts settlements names along route"""
    print("Extracting settlements along route from DB...")

    settlements = []
    current_settlement = None

    # берем часть узлов (не все)
    sampled_nodes = [
        route_nodes[i] for i in range(0, len(route_nodes), sample_interval)
    ]

    with Session(engine) as session:
        for node in sampled_nodes:
            lat = G.nodes[node]["y"]
            lon = G.nodes[node]["x"]

            settlement_name = find_nearest_settlement(session, lat, lon)

            if settlement_name and settlement_name != current_settlement:
                settlements.append(settlement_name)
                current_settlement = settlement_name

    return settlements


def build_route_file_content(route_coords, settlements, total_distance) -> str:
    """Генерирует содержимое файла маршрута в виде строки."""
    content = "Інформація про маршрут\n"
    content += f"Відстань: {round(total_distance / 1000, 2)} км\n\n"

    content += "Точки маршруту:\n"
    if settlements:
        for i, settlement in enumerate(settlements, 1):
            content += f"{i}. {settlement}\n"
    else:
        content += "Немає інформації про міста\n"

    # content += "\nКоординати точок маршруту:\n"
    # for i, coord in enumerate(route_coords, 1):
    #     content += f"{i}. [{coord[1]}, {coord[0]}]\n"

    return content
