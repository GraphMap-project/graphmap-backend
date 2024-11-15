from collections import deque

import networkx as nx
import numpy as np
import osmnx as ox
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from geopy.distance import geodesic

from schemas.route_request import RouteRequest
from utils.utils import build_shortest_path, load_graph

app = FastAPI(title="Graphmap Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ox.config(log_console=True, use_cache=True)

custom_filter = (
    '["highway"~"motorway|trunk|primary|secondary|tertiary|'
    'motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"]'
)

graphml_file = "ukraine_graph.graphml"


@app.post("/shortest_path")
def get_shortest_path(request: RouteRequest):
    start_point = request.start_point
    end_point = request.end_point

    G = load_graph(graphml_file, custom_filter)

    try:
        start_node = ox.nearest_nodes(G, start_point[1], start_point[0])
        end_node = ox.nearest_nodes(G, end_point[1], end_point[0])

        if nx.has_path(G, start_node, end_node):
            # Находим кратчайший путь между двумя узлами с использованием
            # алгоритма Дейкстры
            shortest_path = nx.shortest_path(G, start_node, end_node, weight="length")

            route_coords = [
                (G.nodes[node]["y"], G.nodes[node]["x"]) for node in shortest_path
            ]

            route_data = {"route": route_coords}

            # build_shortest_path(G, shortest_path, start_point, end_point)

            return route_data
        else:
            raise HTTPException(
                status_code=404,
                detail="Невозможно проложить маршрут между двумя точками.",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/distance_matrix")
def get_distance_matrix(request: RouteRequest):
    # TODO: создать подграф из существующего графа и использовать его

    G = load_graph(graphml_file, custom_filter)

    # Объединяем все точки в один список (начальная, промежуточные, конечная)
    points = [request.start_point] + request.intermediate_points + [request.end_point]

    try:
        # Находим ближайшие узлы графа для каждой точки
        nodes = [ox.nearest_nodes(G, point[1], point[0]) for point in points]

        n = len(nodes)
        distance_matrix = np.full((n, n), -1)

        # Параметр для ограничения области поиска (в метрах)
        search_radius = 500  # Можно настроить радиус, например, 500 метров

        def find_nodes_within_radius(graph, center_node, radius):
            """Находит узлы в пределах заданного радиуса от центра."""
            center_coords = (
                graph.nodes[center_node]["y"],
                graph.nodes[center_node]["x"],
            )
            nearby_nodes = set()

            for node, data in graph.nodes(data=True):
                node_coords = (data["y"], data["x"])
                # Рассчитываем расстояние до центра
                if geodesic(center_coords, node_coords).meters <= radius:
                    nearby_nodes.add(node)

            return nearby_nodes

        # Добавляем узлы, которые находятся в пределах заданного радиуса от каждой точки
        all_nodes = set(nodes)
        for node in nodes:
            nearby_nodes = find_nodes_within_radius(G, node, search_radius)
            all_nodes.update(nearby_nodes)

        all_nodes = list(all_nodes)
        m = len(all_nodes)
        distance_matrix = np.full((m, m), -1)

        # Заполняем матрицу расстояний для всех найденных узлов в пределах области
        for i in range(m):
            for j in range(m):
                if i == j:
                    distance_matrix[i, j] = 0
                else:
                    if G.has_edge(all_nodes[i], all_nodes[j]) or G.has_edge(
                        all_nodes[j], all_nodes[i]
                    ):
                        edge_data = G.get_edge_data(
                            all_nodes[i], all_nodes[j]
                        ) or G.get_edge_data(all_nodes[j], all_nodes[i])
                        if edge_data:
                            distance_matrix[i, j] = edge_data[0]["length"]

        return {"distance_matrix": distance_matrix.tolist()}
    except nx.NodeNotFound:
        raise HTTPException(status_code=404, detail="Одна из точек не найдена в графе.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
