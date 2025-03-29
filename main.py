import osmnx as ox
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import create_engine
from models.user import User
from routes.account import account
from routes.shortest_path import shortest_path_route

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
