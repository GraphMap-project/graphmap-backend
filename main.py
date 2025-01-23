import osmnx as ox
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import create_db_and_tables, create_engine
from models.user import User
from routes.shortest_path import shortest_path_route
from routes.account import account

app = FastAPI(title="Graphmap Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


ox.config(log_console=True, use_cache=True)

app.include_router(shortest_path_route)
app.include_router(account)
