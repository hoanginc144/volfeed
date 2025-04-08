""" This file contains the FastAPI application that will serve
as the REST API for the data stored in the TimescaleDB."""
import logging
from typing import Union
import os
from dotenv import load_dotenv
import uvicorn
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from db.query import Query
from processor.models import Instrument, AccountSummary, FetchError
from processor.block_trade_processor import process_block_trade
from api.server import app


# Load environment variables
load_dotenv()
MODE = os.getenv("MODE")

# Set up logging based on the environment
logging.basicConfig(level=logging.DEBUG if MODE == "development" else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@app.get("/")
async def read_root():
    """Root endpoint"""
    return {"Hello": "World"}


@app.get("/api/{path}", response_model=list[Union[Instrument, AccountSummary, FetchError]])
async def read_data(path: str):
    """Create sql query based on the path parameter and fetch data from the database."""
    ts = app.state.db
    sql = Query.get(path)

    try:
        data = await ts.query(sql)

        if path == "blocktrade2":
            data = process_block_trade(data)

        return JSONResponse(content={"data": jsonable_encoder(data)})
    except Exception as e:
        logging.error("Error fetching data: %s", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == '__main__':
    uvicorn.run("rest:app", host="127.0.0.1", port=8000, reload=True)
