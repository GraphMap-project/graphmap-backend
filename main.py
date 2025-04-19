import osmnx as ox
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.account import account
from routes.shortest_path import shortest_path_route
from utils.utils import load_graph

custom_filter = (
    '["highway"~"motorway|trunk|primary|secondary|tertiary|'
    "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|"
    'residential"]'
)
# custom_filter = (
#     '["highway"~"motorway|trunk|primary|secondary|tertiary|'
#     'motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|'
#     'unclassified|residential|living_street|service"]'
#     '["area"!~"yes"]'
#     '["service"!~"parking_aisle"]'
# )

graph_pickle_file = "ukraine_graph"

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
async def load_graph_on_startup():
    app.state.graph = load_graph(graph_pickle_file, custom_filter)
    print("Graph loaded and ready to use.")
