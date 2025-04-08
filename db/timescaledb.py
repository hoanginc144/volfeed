"""TimescaleDB client"""
import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import asyncpg


# Load environment variables
load_dotenv()
CONNECTION = os.getenv("CONNECTION")


class TimescaleDb:
    """TimescaleDB client using connection pooling"""

    def __init__(self, db_name):
        self.pool = None
        self.db_name = db_name

    async def connect(self) -> None:
        """Initialize a connection pool to the database"""
        try:
            self.pool = await asyncpg.create_pool(dsn=CONNECTION + self.db_name,
                                                  min_size=1,
                                                  max_size=3)
            logging.info("Connection pool created successfully")
        except asyncpg.exceptions.PostgresError as e:
            logging.error("Error creating connection pool: %s", e)

    async def close(self) -> None:
        """Close all connections in the pool"""
        await self.pool.close()
        logging.info("Connection pool closed.")

    async def insert_batch(self, table_name: str, data_list: List[Dict[str, Any]]) -> None:
        """Insert a batch of data into the database"""
        columns = ', '.join(data_list[0].keys()) + ', time'
        placeholders = ', '.join(
            f"${i+1}" for i in range(len(data_list[0]))) + ', NOW()'
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        data_tuples = [tuple(item.values()) for item in data_list]

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    logging.info("Inserting into '%s'", table_name)
                    await conn.executemany(sql, data_tuples)
                    logging.info("'%s' data inserted.", table_name)
                except asyncpg.exceptions.PostgresError as e:
                    logging.error(
                        "Error inserting into '%s': %s", table_name, e)

    async def query(self, sql: str) -> List[Dict[str, Any]] | Dict[str, Any]:
        """Get data from the database"""
        async with self.pool.acquire() as conn:
            try:
                records = await conn.fetch(sql)
                logging.info("Fetched '%s'", sql)
                return [dict(record) for record in records]
            except Exception as e:
                logging.error("Error fetching '%s': %s", sql, e)
                return None
