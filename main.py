import osmnx as ox
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from config.database import engine
from routes.account import account
from routes.shortest_path import shortest_path_route
from utils.db_utils import load_settlements_from_geonames
from utils.landmark_utils import (
    get_regional_center_nodes,
    preprocess_landmarks_distances,
    select_global_landmarks,
)
from utils.utils import load_graph

custom_filter = (
    '["highway"~"motorway|trunk|primary|secondary|tertiary|'
    "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|"
    'unclassified|residential|living_street|service"]'
    '["area"!~"yes"]'
    '["service"!~"parking_aisle"]'
)

graph_pickle_file = "detailed_ukraine_graph"
REGIONAL_CENTERS = [
    "Kyiv",
    "Lviv",
    "Odesa",
    "Kharkiv",
    "Dnipro",
    "Zaporizhzhia",
    "Vinnytsia",
]


app = FastAPI(title="Graphmap Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ox.config(log_console=True, use_cache=True)

app.include_router(shortest_path_route)
app.include_router(account)


@app.on_event("startup")
async def load_data_on_startup():
    app.state.graph = load_graph(graph_pickle_file, custom_filter)
    print("Graph loaded and ready to use.")

    with Session(engine) as session:
        try:
            load_settlements_from_geonames(session)
        except Exception as e:
            print(f"Error loading settlements: {e}")

    print("Selecting landmarks...")
    city_names = [f"{city}, Ukraine" for city in REGIONAL_CENTERS]
    center_nodes = get_regional_center_nodes(app.state.graph, city_names)

    app.state.landmarks = select_global_landmarks(
        app.state.graph, regional_centers=center_nodes, k=5
    )

    print("Preprocessing landmarks distances...")
    app.state.landmark_distances = preprocess_landmarks_distances(
        app.state.graph, app.state.landmarks
    )

    print("Landmarks loaded and ready to use.")
