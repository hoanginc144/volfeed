"""Conductor module to orchestrate the data processing pipeline"""
import logging
import os
import asyncio
from typing import List, Dict, Any
import yaml
from dotenv import load_dotenv
from api.deribit import DeribitClient
from db.timescaledb import TimescaleDb
from processor.data_processor import DataProcessor
from utils.utils import cleanup

# Load environment variables
load_dotenv()

MODE = os.getenv("MODE")
PARAM_PATH = os.path.dirname(
    os.path.realpath(__file__)) + "/../parameters.yaml"


class Conductor:
    """Class to orchestrate the data processing pipeline"""

    def __init__(self, db_only: bool = False):
        self.params = [
            ("account", "private/get_account_summary",
             {"currency": "BTC", "extended": "false"}),
            ("market", "public/get_book_summary_by_currency",
             {"currency": "BTC", "kind": "option"}),
            ("price", "public/get_index_price", {"index_name": "btc_usd"}),
        ]
        self._load_initial_settings_()
        if not db_only:
            self.deribit = DeribitClient()
        else:
            self.deribit = None
        self.db = TimescaleDb(self.db_name)

    def _load_initial_settings_(self):
        with open(PARAM_PATH, "r", encoding="utf-8") as f:
            settings = yaml.safe_load(f)[MODE]
            self._load_settings_(settings)

    def _load_settings_(self, settings: Dict):
        self.db_name = settings["db_name"]
        self.update_interval = settings["update_interval"]

    async def refresh_settings(self):
        """Refresh settings from the parameters.yaml file every 10 seconds"""
        while True:
            await asyncio.sleep(60)
            with open(PARAM_PATH, "r", encoding="utf-8") as f:
                settings = yaml.safe_load(f)[MODE]
                self._load_settings_(settings)

    async def setup_session(self):
        """Authenticate with the Deribit API and connect to the database"""
        if self.deribit is not None:
            await self.deribit.authenticate()
        await self.db.connect()

    async def get_and_process_data(self, processor_type: str,
                                   endpoint: str,
                                   payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get and process data from the Deribit API"""
        # Get data
        logging.info("Getting %s data...", processor_type)
        data = await self.deribit.get(endpoint, payload)

        # Process data
        logging.info("Preparing %s data...", processor_type)
        processor = DataProcessor(processor_type, data)
        processed_data = await processor.process()
        logging.info("%s data processed", processor_type)
        return processed_data

    async def consolidate_data(self):
        """Concurrently get and process account, market, and price data from the Deribit API"""
        tasks = [self.get_and_process_data(*param) for param in self.params]
        account_data, \
            market_data, \
            price_data = await asyncio.gather(*tasks)

        return [("btc_account_summary", account_data),
                ("btc_option", market_data),
                ("btc_price", price_data)]

    async def insert_data(self, inserts):
        """Insert consolidated data into the database"""
        insert_tasks = [self.db.insert_batch(*data)
                        for data in inserts]
        await asyncio.gather(*insert_tasks)

    async def initiate_pipeline(self):
        """Orchestrate the data processing pipeline"""
        while True:
            print("-" * 50)
            inserts = await self.consolidate_data()
            await self.insert_data(inserts)
            await asyncio.sleep(self.update_interval)

    async def end_session(self):
        """Close the HTTP session and the database connection"""
        if self.deribit is not None:
            await cleanup(self.deribit, self.db)
        else:
            await cleanup(self.db)
