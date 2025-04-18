import networkx as nx
import osmnx as ox
from fastapi import APIRouter, HTTPException, Request

from schemas.route_request import RouteRequest
from utils.utils import (
    alt_heuristic,
    auto_select_landmarks,
    extract_edge_geometries,
    filter_threats,
    load_graph,
    plot_shortest_path,
    preprocess_landmarks,
)

shortest_path_route = APIRouter()


def prepare_graph_and_nodes(request: RouteRequest, app):
    points = [request.start_point] + \
        request.intermediate_points + [request.end_point]

    G = app.state.graph  # G = load_graph(graphml_file, custom_filter)

    if request.threats:
        G = filter_threats(G, request.threats)

    nodes = [ox.nearest_nodes(G, lon, lat) for lat, lon in points]
    return G, nodes, points


def build_full_route(G, nodes, points, path_func):
    full_route = []
    for i in range(len(nodes) - 1):
        start_node, end_node = nodes[i], nodes[i + 1]

        if not nx.has_path(G, start_node, end_node):
            raise HTTPException(
                status_code=404,
                detail=f"Can't find path between {points[i]} and {points[i + 1]}.",
            )

        segment_path = path_func(G, start_node, end_node)
        full_route.extend(segment_path[:-1])  # Avoid duplication

    full_route.append(nodes[-1])
    return full_route


def dijkstra_algorithm(G, u, v):
    return nx.shortest_path(G, u, v, weight="length")


def alt_algorithm(G, u, v):
    landmarks = auto_select_landmarks(G, u, v)
    landmark_distances = preprocess_landmarks(G, landmarks)

    return nx.astar_path(
        G,
        u,
        v,
        weight="length",
        heuristic=lambda u_, v_: alt_heuristic(
            u_, v_, landmarks, landmark_distances),
    )


@shortest_path_route.post("/shortest_path")
def get_shortest_path(request: RouteRequest, app: Request):
    try:
        G, nodes, points = prepare_graph_and_nodes(
            request, app.app)

        if request.algorithm == "dijkstra":
            path_func = dijkstra_algorithm

        elif request.algorithm == "alt":
            path_func = alt_algorithm

        full_route = build_full_route(G, nodes, points, path_func)

        route_coords = extract_edge_geometries(G, full_route)

        # Расчёт общей длины маршрута
        total_distance = 0
        for i in range(len(full_route) - 1):
            u, v = full_route[i], full_route[i + 1]
            edge_data = G.get_edge_data(u, v)
            # В графе может быть несколько рёбер между узлами (мультиграф)
            if isinstance(edge_data, dict):
                if 0 in edge_data:
                    total_distance += edge_data[0].get("length", 0)
                else:
                    # если это обычный граф, а не мультиграф
                    total_distance += edge_data.get("length", 0)

        plot_shortest_path(
            G, full_route, points, request.start_point, request.end_point)

        return {
            "route": route_coords,
            # Convert to kilometers
            "distance": round(total_distance / 1000, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
