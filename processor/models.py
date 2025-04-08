"""Model module"""
from datetime import datetime
from pydantic import BaseModel


class Instrument(BaseModel):
    """Instrument model"""
    currency: str
    expiry_date: datetime
    strike: float
    option_type: str
    underlying_price: float
    mark_price: float
    mid_price: float
    bid_price: float
    ask_price: float
    iv: float
    delta: float
    net_delta: float
    gamma: float
    theta: float
    vega: float
    time: str
    creation_timestamp: datetime


class AccountSummary(BaseModel):
    """Account summary model"""
    equity: float
    balance: float
    futures_pl: float
    options_pl: float
    initial_margin: float
    maintenance_margin: float
    delta_total: float
    options_delta: float
    options_gamma: float
    options_theta: float
    options_vega: float
    time: datetime


class FetchError(BaseModel):
    """Fetch error model"""
    error: str
