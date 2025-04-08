""" This script extracts the trade information from the messages
in the Telegram channel and stores them in a list of dictionaries."""
import logging
import os
import re
import asyncio
from typing import List, Dict, Any, Tuple
from datetime import datetime
from telethon import TelegramClient
from dotenv import load_dotenv
import pytz
from conductor.conductor import Conductor


load_dotenv()

MODE = os.getenv("MODE")

# Set up logging based on the environment
logging.basicConfig(level=logging.DEBUG if MODE == "development" else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Replace these with your own values
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
# You can use the channel's username or its channel ID
CHANNEL_USERNAME = 'greekslive_notifications2'

# Create the client and connect
client = TelegramClient('session_name', api_id, api_hash)
conductor = Conductor(db_only=True)


async def main():
    """This function extracts the trade information from the messages"""
    # Connect to the client
    await client.start()
    channel = await client.get_entity(CHANNEL_USERNAME)
    await conductor.setup_session()

    try:
        while True:
            trades_list = await extract_trades(channel)
            await insert_trades(trades_list)
            await asyncio.sleep(15 * 60)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Interrupted by user, exiting...")
    finally:
        await client.disconnect()
        await conductor.end_session()


async def insert_trades(trades_list: List[Dict[str, Any]]) -> None:
    """This function inserts the trades into the database"""
    # If there new trades, insert them into the database
    if trades_list:
        await conductor.db.insert_batch("block_trade", trades_list)
    else:
        logging.info("No new trades to insert.")


async def extract_trades(channel) -> List[Dict[str, Any]]:
    """Create a list of trades from the messages in the channel"""
    trades_list = []

    # Get messages from the channel
    async for message in client.iter_messages(channel, limit=3000):
        if ("BTC" in message.text and "Block Trade" in message.text):
            # Populate the list of trades to be stored in the dictionary
            consolidate_trades(trades_list, message)
        else:
            logging.info("No trades found in the message")

    # Filter out the trades that are already in the database
    # trades_list = await filter_trades(trades_list)

    return trades_list


def consolidate_trades(trades_list: List, message: Any):
    """Consolidate the trades into a list of dictionaries"""
    # Extract the trade information from the message
    trades = parse_trade_info(message.text)
    for trade in trades:
        currency, expiry_date, strike, option_type = parse_instrument(
            trade[1])

        trades_list.append({
            "time_of_trade": pytz.utc.localize(datetime.strptime(trade[8], "%Y-%m-%d %H:%M:%S")),
            "id": message.id,
            "direction": trade[0],
            "expiry_date": expiry_date,
            "currency": currency,
            "strike": int(strike),
            "option_type": option_type.lower(),
            "quantity": float(trade[2].replace(',', '')),
            "option_price": float(trade[3]),
            "iv": float(trade[4]),
            "index_price": float(trade[5].replace(',', '')),
            "total_premium_btc": round(float(trade[3]) * float(trade[2].replace(',', '')), 5),
            "total_premium_usd": float(trade[6].replace(',', '')),
            "greeks_live_url": trade[7]
        })


def parse_instrument(instrument: str) -> Tuple[str, str, str, str]:
    """Parse the instrument name and return the relevant values"""
    instrument = tuple(instrument.split('-'))
    currency, expiry_date, strike, option_type = instrument

    # convert the expiry date to a UTC datetime object and set the hour to 8:00 AM
    expiry_date = pytz.utc.localize(datetime.strptime(expiry_date, "%d%b%y")) \
        .replace(hour=8, minute=0, second=0, microsecond=0)

    return currency, expiry_date, strike, option_type


def parse_trade_info(message: str) -> List[Any]:
    """This function extracts the trade information from the messages"""

    # Define the pattern to extract the trade information
    trade_pattern = re.compile(
        r"\*\*Contract:\*\* (\w+) (BTC-\d{1,2}[A-Z]{3}\d{2}-\d{4,6}-[C|P])\n"
        r"\*\*Transaction Info:\*\* ([\d,\.]+) @ ฿ ([\d\.]+)\n"
        r"\*\*Volatility:\*\* ([\d\.]+)%\n"
        r"\*\*Index:\*\* \$([\d,]+\.\d{2})\n"
        r"\*\*Premium Value in USD:\*\* \$([\d,]+\.\d{2})"
    )
    # Search for matches in the message
    trades = trade_pattern.findall(message)

    try:
        url = re.search(
            r"\[View P&L Analysis 👈\]\(([^)]+)\)", message).group(1)
        time_of_trade = re.search(
            r"\*\*Time:\*\* ([\d-]+\s[\d:]+)", message).group(1)
    except AttributeError:
        logging.error("No relevant info found in the message")

    # append the url and time of the trade to individual trades found in trades
    trades = [trade + (url, time_of_trade) for trade in trades]

    return trades


async def filter_trades(trades_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """This function filters out the trades that are already in the database"""
    # create a list of unique ids found in the trades_list
    unique_ids = list(set([trade["id"] for trade in trades_list]))

    # query the database for the ids in the unique_ids list
    query = f"""SELECT DISTINCT(id)
                FROM block_trade
                WHERE id IN({','.join([str(id) for id in unique_ids])})"""
    trades = await conductor.db.query(query)
    existing_ids = list(set([trade["id"] for trade in trades]))

    # filter out the trades that are already in the database
    trades_list = [trade
                   for trade in trades_list if trade["id"] not in existing_ids]
    return trades_list

if __name__ == "__main__":
    asyncio.run(main())
