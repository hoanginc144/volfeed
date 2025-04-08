""" Process data and calculate greeks """
from typing import List, Dict, Any
from dotenv import load_dotenv
from utils.greeks import OptionData

# Load environment variables
load_dotenv()


class DataProcessor:
    """Process data and calculate greeks"""

    def __init__(self, data_type: str, data: List[Dict[str, Any]] | Dict[str, Any]):
        self.data_type = data_type
        self.data = data
        self.processed_data = []

    async def process(self) -> List[Dict[str, Any]]:
        """Process data based on the data type"""
        if self.data_type == "market":
            self.processed_data = [
                self.process_market_data(item) for item in self.data]
        elif self.data_type == "account":
            self.processed_data = [self.process_account_data(self.data)]
        elif self.data_type == "price":
            self.processed_data = [self.process_price_data(self.data)]
        return self.processed_data

    def process_market_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data"""
        option = OptionData()
        return option.process_data(item)

    def process_account_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process account data"""
        return {
            "equity": item["equity"],
            "balance": item["balance"],
            "futures_pl": item["futures_pl"],
            "options_pl": item["options_pl"],
            "initial_margin": item["initial_margin"],
            "maintenance_margin": item["maintenance_margin"],
            "options_delta": item["options_delta"],
            "delta_total": item["delta_total"],
            "options_vega": item["options_vega"],
            "options_theta": item["options_theta"],
            "options_gamma": item["options_gamma"]
        }

    def process_price_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process price data"""
        return {"index_price": item["index_price"]}
