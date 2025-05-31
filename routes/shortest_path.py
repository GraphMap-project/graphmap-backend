import uuid
from io import BytesIO

import networkx as nx
import osmnx as ox
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from schemas.route_request import RouteRequest
from utils.utils import (
    alt_heuristic,
    build_route_file_content,
    extract_edge_geometries,
    filter_threats,
    get_settlements_along_route,
    plot_shortest_path,
)

shortest_path_route = APIRouter()

ROUTES_CACHE = {}


def prepare_graph_and_nodes(request: RouteRequest, app):
    points = [request.start_point] + request.intermediate_points + [request.end_point]

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


def alt_algorithm(G, u, v, landmarks, landmark_distances):
    return nx.astar_path(
        G,
        u,
        v,
        weight="length",
        heuristic=lambda u_, v_: alt_heuristic(u_, v_, landmarks, landmark_distances),
    )


@shortest_path_route.post("/shortest_path")
def get_shortest_path(request: RouteRequest, app: Request):
    try:
        G, nodes, points = prepare_graph_and_nodes(request, app.app)

        if request.algorithm == "dijkstra":
            path_func = dijkstra_algorithm

        elif request.algorithm == "alt":
            landmarks = app.app.state.landmarks
            landmark_distances = app.app.state.landmark_distances

            def path_func(G_, u_, v_):
                return alt_algorithm(G_, u_, v_, landmarks, landmark_distances)

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
            G,
            full_route,
            points,
            request.start_point,
            request.end_point,
            landmarks=app.app.state.landmarks,
        )

        route_id = str(uuid.uuid4())

        ROUTES_CACHE[route_id] = {
            "full_route": full_route,
            "route_coords": route_coords,
            "total_distance": total_distance,
        }

        response = {
            "route": route_coords,
            "distance": round(total_distance / 1000, 2),
            "route_id": route_id,
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@shortest_path_route.get("/generate_route_file/{route_id}")
async def generate_route_file(route_id: str, app: Request):
    try:
        if route_id not in ROUTES_CACHE:
            raise HTTPException(status_code=404, detail="Route not found")

        data = ROUTES_CACHE[route_id]
        G = app.app.state.graph
        full_route = data["full_route"]
        route_coords = data["route_coords"]
        total_distance = data["total_distance"]

        settlements = await get_settlements_along_route(
            G, full_route, sample_interval=20
        )

        file_content = build_route_file_content(
            route_coords, settlements, total_distance
        )

        file_stream = BytesIO(file_content.encode("utf-8"))

        return StreamingResponse(
            file_stream,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=route.txt"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
