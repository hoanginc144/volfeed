""" Calculate greeks """
from datetime import datetime
from typing import Dict, Any, NamedTuple
import logging
import pytz
from dotenv import load_dotenv
import py_vollib.black_scholes.greeks.numerical as greeks
from py_vollib.black_scholes.implied_volatility import implied_volatility
from py_lets_be_rational.exceptions import BelowIntrinsicException

# Load environment variables
load_dotenv()


class InstrumentData(NamedTuple):
    """Option data class"""
    price: float
    s: float
    k: float
    t: float
    r: float
    flag: str
    name: str


class OptionData:
    """Calculate greeks and implied volatility"""

    def process_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data and calculate greeks"""
        yte, stk_price, opt_type, exp_date = self.parse_exp(
            item["instrument_name"])
        instrument_data = InstrumentData(item["mark_price"] * item["underlying_price"],
                                         item["underlying_price"],
                                         stk_price,
                                         yte,
                                         0,
                                         opt_type,
                                         item["instrument_name"])
        delta, vega, theta, gamma, iv = OptionData.calc_greeks(instrument_data)
        creation_timestamp = datetime.fromtimestamp(
            item["creation_timestamp"] / 1000, pytz.utc)

        return {
            "currency": item["base_currency"],
            "expiry_date": exp_date,
            "strike": stk_price,
            "option_type": opt_type,
            "mid_price": self.rnd_to_6(item["mid_price"]),
            "ask_price": self.rnd_to_6(item["ask_price"]),
            "mark_price": self.rnd_to_6(item["mark_price"]),
            "bid_price": self.rnd_to_6(item["bid_price"]),
            "underlying_price": self.rnd_to_6(item["underlying_price"]),
            "delta": delta,
            "net_delta": delta - item["mark_price"],
            "vega": vega,
            "theta": theta,
            "gamma": gamma,
            "iv": iv,
            "creation_timestamp": creation_timestamp
        }

    @staticmethod
    def rnd_to_6(n: float) -> float:
        """Round to 6 decimal places"""
        return round(n, 6) if n is not None else None

    @staticmethod
    def parse_exp(string: str) -> tuple[float, int, str, datetime, str]:
        """Parse the instrument name and return the relevant values
        The format of the instrument name should be similar to BTC-12APR24-80000-C"""
        currency, date_string, strike, option = string.split('-')
        stk_price = int(strike)
        option_type = option.lower()
        exp_date = datetime \
            .strptime(date_string, '%d%b%y') \
            .replace(hour=8, tzinfo=pytz.utc)
        time_to_exp = (exp_date - datetime.now(pytz.utc)) \
            .total_seconds() / (365 * 24 * 3600)
        return time_to_exp, stk_price, option_type, exp_date

    @staticmethod
    def calc_greeks(i: InstrumentData) -> tuple[float, float, float, float, float]:
        """Calculate greeks using py_vollib, note that sigma will be returned as a percentage
        hence the multiplication by 100 in the return statement."""
        try:
            sigma = implied_volatility(i.price, i.s, i.k, i.t, i.r, i.flag)
        except BelowIntrinsicException:
            logging.warning(
                "%s IV calculation failed, returning a default value", i.name)
            sigma = 0.01
        delta = greeks.delta(i.flag, i.s, i.k, i.t, i.r, sigma)
        vega = greeks.vega(i.flag, i.s, i.k, i.t, i.r, sigma)
        theta = greeks.theta(i.flag, i.s, i.k, i.t, i.r, sigma)
        gamma = greeks.gamma(i.flag, i.s, i.k, i.t, i.r, sigma)
        return delta, vega, theta, gamma, sigma * 100
