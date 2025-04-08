"""This script gets account summary, option market, and price data
from the Deribit API and inserts it into a TimescaleDB database."""

# load external modules
import asyncio
import logging
import os

from dotenv import load_dotenv

# load project modules
from conductor.conductor import Conductor

# Load environment variables
load_dotenv()
MODE = os.getenv("MODE")

# Set up logging based on the environment
logging.basicConfig(
    level=logging.DEBUG if MODE == "development" else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def main():
    """Main function to fetch data from the Deribit API and insert it into the database."""
    try:
        conductor = Conductor()
        await conductor.setup_session()
        await asyncio.gather(
            asyncio.create_task(conductor.refresh_settings()),
            asyncio.create_task(conductor.initiate_pipeline()),
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Program interrupted. Gracefully exiting...")
    finally:
        await conductor.end_session()
        logging.info("Program exited.")


if __name__ == "__main__":
    asyncio.run(main())
