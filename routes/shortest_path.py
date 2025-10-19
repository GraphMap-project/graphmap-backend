import uuid
from io import BytesIO

import networkx as nx
import osmnx as ox
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import select

from config.database import SessionDep
from models.route import Route
from models.user import User
from routes.account import get_current_user
from schemas.route_request import RouteRequest
from schemas.route_save import RouteSave
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

        # plot_shortest_path(
        #     G,
        #     full_route,
        #     points,
        #     request.start_point,
        #     request.end_point,
        #     landmarks=app.app.state.landmarks,
        # )

        route_id = str(uuid.uuid4())

        ROUTES_CACHE[route_id] = {
            "full_route": full_route,
            "route_coords": route_coords,
            "total_distance": total_distance,
            "algorithm": request.algorithm,
            "start_point": request.start_point,
            "end_point": request.end_point,
            "intermediate_points": request.intermediate_points,
            "threats": request.threats,
            "start_point_name": request.start_point_name,
            "end_point_name": request.end_point_name,
            "intermediate_point_names": request.intermediate_point_names,
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


@shortest_path_route.post("/save_route")
def save_route(
    route_data: RouteSave,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Save a route to the database for the authenticated user."""
    try:
        if route_data.route_id not in ROUTES_CACHE:
            raise HTTPException(status_code=404, detail="Route not found")

        cached_route = ROUTES_CACHE[route_data.route_id]

        new_route = Route(
            id=route_data.route_id,
            user_id=current_user.id,
            name=route_data.name,
            algorithm=cached_route["algorithm"],
            total_distance=cached_route["total_distance"],
            route_coords=cached_route["route_coords"],
            full_route_nodes=cached_route["full_route"],
            start_point=cached_route["start_point"],
            end_point=cached_route["end_point"],
            intermediate_points=cached_route["intermediate_points"],
            threats=cached_route["threats"],
            start_point_name=cached_route["start_point_name"],
            end_point_name=cached_route["end_point_name"],
            intermediate_point_names=cached_route["intermediate_point_names"],
        )

        session.add(new_route)
        session.commit()
        session.refresh(new_route)

        return {
            "message": "Route saved successfully",
            "route_id": str(new_route.id),
            "name": new_route.name,
            "distance_km": round(new_route.total_distance / 1000, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@shortest_path_route.get("/routes")
def get_user_routes(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get all saved routes for the authenticated user."""
    try:
        statement = select(Route).where(Route.user_id == current_user.id)

        statement = statement.order_by(Route.created_at.desc())
        routes = session.exec(statement).all()

        return {
            "count": len(routes),
            "routes": [
                {
                    "id": str(route.id),
                    "name": route.name,
                    "algorithm": route.algorithm,
                    "distance_km": round(route.total_distance / 1000, 2),
                    "created_at": route.created_at.isoformat(),
                }
                for route in routes
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@shortest_path_route.get("/routes/{route_id}")
def get_route_details(
    route_id: str, session: SessionDep, current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific saved route.
    Includes full route coordinates for map visualization.
    """

    try:
        route_uuid = uuid.UUID(route_id)

        statement = select(Route).where(
            Route.id == route_uuid, Route.user_id == current_user.id
        )
        route = session.exec(statement).first()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        return {
            "id": str(route.id),
            "name": route.name,
            "algorithm": route.algorithm,
            "total_distance": route.total_distance,
            "distance_km": round(route.total_distance / 1000, 2),
            "route_coords": route.route_coords,
            "start_point": route.start_point,
            "end_point": route.end_point,
            "intermediate_points": route.intermediate_points or [],
            "start_point_name": route.start_point_name,
            "end_point_name": route.end_point_name,
            "intermediate_point_names": route.intermediate_point_names or [],
            "created_at": route.created_at.isoformat(),
            "updated_at": route.updated_at.isoformat() if route.updated_at else None,
            "threats": route.threats or [],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid route ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@shortest_path_route.delete("/routes/{route_id}")
def delete_route(
    route_id: str, session: SessionDep, current_user: User = Depends(get_current_user)
):
    """Delete a saved route permanently."""
    try:
        route_uuid = uuid.UUID(route_id)

        statement = select(Route).where(
            Route.id == route_uuid, Route.user_id == current_user.id
        )
        route = session.exec(statement).first()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        session.delete(route)
        session.commit()

        return {"message": "Route deleted successfully", "route_id": route_id}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid route ID format")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
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
