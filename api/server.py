"""This module creates a FastAPI application and establishes a connection to the database"""
from contextlib import asynccontextmanager
import os
from typing import Dict, Any
import yaml
from fastapi import FastAPI
from dotenv import load_dotenv
from db.timescaledb import TimescaleDb

# Load environment variables
load_dotenv()
MODE = os.getenv("MODE")
PARAM_PATH = os.path.dirname(
    os.path.realpath(__file__)) + "/../parameters.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create a database connection pool when the application starts"""
    with open(PARAM_PATH, "r", encoding="utf-8") as f:
        settings: Dict[str, Any] = yaml.safe_load(f)[MODE]
        db_name: str = settings["db_name"]
    app.state.db = TimescaleDb(db_name)
    await app.state.db.connect()
    yield
    # Teardown the database connection
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
