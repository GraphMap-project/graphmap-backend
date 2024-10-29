import networkx as nx
import osmnx as ox
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
