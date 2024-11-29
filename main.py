from collections import deque
from math import sqrt

import networkx as nx
import numpy as np
import osmnx as ox
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from geopy.distance import geodesic

from schemas.route_request import RouteRequest
from utils.utils import build_shortest_path, build_shortest_path2, load_graph

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
    try:
        points = (
            [request.start_point] + request.intermediate_points + [request.end_point]
        )
        G = load_graph(graphml_file, custom_filter)

        # Знайти найближчі вузли для кожної точки
        nodes = [ox.nearest_nodes(G, point[1], point[0]) for point in points]

        # Перевіряємо наявність шляху між кожною парою послідовних точок
        full_route = []
        for i in range(len(nodes) - 1):
            start_node = nodes[i]
            end_node = nodes[i + 1]

            if not nx.has_path(G, start_node, end_node):
                raise HTTPException(
                    status_code=404,
                    detail=f"Can't find path between {points[i]} and {points[i+1]}.",
                )

            # Знаходимо найкоротший шлях для поточного сегмента
            segment_path = nx.shortest_path(G, start_node, end_node, weight="length")
            full_route.extend(
                segment_path[:-1]
            )  # Виключаємо останній вузол, щоб уникнути дублювання

        # Додаємо останній вузол останнього сегмента
        full_route.append(nodes[-1])

        build_shortest_path2(G, full_route, points)

        # Генеруємо координати маршруту
        route_coords = [(G.nodes[node]["y"], G.nodes[node]["x"]) for node in full_route]

        route_data = {"route": route_coords}
        return route_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/distance_matrix")
def get_distance_matrix(request: RouteRequest):
    G = load_graph(graphml_file, custom_filter)

    start_coords = (request.start_point[1], request.start_point[0])
    end_coords = (request.end_point[1], request.end_point[0])
    start_node = ox.nearest_nodes(G, request.start_point[1], request.start_point[0])
    end_node = ox.nearest_nodes(G, request.end_point[1], request.end_point[0])

    intermediate_nodes = [
        ox.nearest_nodes(G, point[1], point[0]) for point in request.intermediate_points
    ]

    route_nodes = [start_node] + [end_node]

    search_radius = geodesic(start_coords, end_coords).meters

    print(search_radius)

    nearby_nodes = set()
    for node in route_nodes:
        nearby_nodes.update(
            nx.ego_graph(
                G, node, center=False, radius=search_radius, distance="length"
            ).nodes
        )

    subgraph = G.subgraph(nearby_nodes)

    shortest_path = nx.shortest_path(subgraph, start_node, end_node, weight="length")

    # Генерируем матрицу смежности
    adj_matrix = nx.adjacency_matrix(subgraph, weight="length")

    print(adj_matrix)

    build_shortest_path(subgraph, shortest_path, start_coords, end_coords)

    return {"distance_matrix": "Builded Successfuly"}
