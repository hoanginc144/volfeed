""" Monitor the portfolio delta and send a Telegram alert if it exceeds a threshold. """
import asyncio
import json
import os
import logging
from typing import Dict, Any
import websockets
import requests
import yaml
from dotenv import load_dotenv


load_dotenv()
MODE = os.getenv("MODE")
PARAM_PATH = os.path.dirname(
    os.path.realpath(__file__)) + "/parameters.yaml"

# Set up logging based on the environment
logging.basicConfig(level=logging.DEBUG if MODE == "development" else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


async def get_threshold():
    """Load the delta threshold from the parameters file"""
    try:
        with open(PARAM_PATH, "r", encoding="utf-8") as f:
            settings: Dict[str, Any] = yaml.safe_load(f)[MODE]
            delta_threshold: float = settings["delta_threshold"]
        return delta_threshold
    except FileNotFoundError as e:
        logging.error("Error loading the parameters file: %s", e)
        return None


async def authenticate(websocket):
    """Authenticate the client"""
    try:
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        auth_message = {
            "jsonrpc": "2.0",
            "method": "public/auth",
            "params": {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            },
            "id": 42
        }
        await websocket.send(json.dumps(auth_message))
        logging.info("Authenticated successfully")
    except Exception as e:
        logging.error("Error authenticating the client: %s", e)


async def subscribe(websocket):
    """Subscribe to the portfolio channel"""
    try:
        subscribe_message = {
            "jsonrpc": "2.0",
            "method": "private/subscribe",
            "params": {
                "channels": ["user.portfolio.btc"]
            },
            "id": 42
        }
        await websocket.send(json.dumps(subscribe_message))
        logging.info("Subscribed to the portfolio channel")
    except Exception as e:
        logging.error("Error subscribing to the portfolio channel: %s", e)


async def monitor_portfolio():
    """Monitor the portfolio delta and send a Telegram alert if it exceeds a threshold."""

    # Load environment variables
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    async with websockets.connect("wss://www.deribit.com/ws/api/v2") as websocket:
        await authenticate(websocket)
        await subscribe(websocket)

        while True:
            message = await websocket.recv()
            delta_threshold = await get_threshold()
            data = json.loads(message)

            if "params" in data:
                delta = data["params"]["data"]["delta_total"]
                if delta and abs(delta) > delta_threshold:
                    message = f"Delta exceeds threshold of {delta_threshold}: {delta}"
                    send_telegram_alert(telegram_bot_token,
                                        telegram_chat_id, message)
                else:
                    logging.info("Delta is normal: %s", delta)
                    # message = f"Delta is normal: {delta}"
                    # send_telegram_alert(telegram_bot_token,
                    #                     telegram_chat_id, message)
            else:
                logging.info("No data in the message")


def send_telegram_alert(bot_token: str, chat_id: int, message: str) -> None:
    """Send a Telegram alert"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            logging.error("Error sending Telegram alert: %s", response.text)
    except requests.RequestException as e:
        logging.error("Error sending Telegram alert: %s", e)


if __name__ == "__main__":
    try:
        asyncio.run(monitor_portfolio())
    except KeyboardInterrupt:
        logging.info("Stopped by user. Exiting the program")
