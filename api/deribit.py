"""Deribit API client"""
import os
import logging
from typing import Dict, Any
import asyncio
from datetime import datetime
import aiohttp
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class DeribitClient:
    """Deribit API client """

    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.session = aiohttp.ClientSession()
        self.access_token = None
        self.refresh_token = None
        self.expires_in = 0
        self.tokens_last_updated = datetime.now()

    async def authenticate(self) -> None:
        """Authenticate the client and get the access token"""
        try:
            # Authenticate the client
            if not self.access_token:
                url = 'https://www.deribit.com/api/v2/public/auth'
                payload = {"grant_type": "client_credentials",
                           "client_id": self.client_id, "client_secret": self.client_secret}
                async with self.session.get(url, params=payload) as response:
                    res = await response.json()
                    self.access_token = res['result']['access_token']
                    self.refresh_token = res['result']['refresh_token']
                    self.expires_in = res['result']['expires_in'] - 60
                    logging.info("Authenticated successfully")
        except aiohttp.ClientError as e:
            logging.error("Error authenticating the client: %s", e)

    async def refresh_authentication(self) -> str:
        """Refresh the authentication token"""
        try:
            url = 'https://www.deribit.com/api/v2/public/auth'
            payload = {"grant_type": "refresh_token",
                       "refresh_token": self.refresh_token}
            async with self.session.get(url, params=payload) as response:
                res = await response.json()
                self.access_token = res['result']['access_token']
                self.refresh_token = res['result']['refresh_token']
                self.expires_in = res['result']['expires_in'] - 60
                logging.info("Authentication tokens refreshed")
        except aiohttp.ClientError as e:
            logging.error("Error refreshing the authentication token: %s", e)

    async def get(self, end_point: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a GET request to the Deribit API"""
        try:
            url = f'https://www.deribit.com/api/v2/{end_point}'
            headers = {}
            if "private" in end_point:
                # Check if the access token has expired
                elapsed = (datetime.now() -
                           self.tokens_last_updated).total_seconds()
                if elapsed >= self.expires_in:
                    await self.refresh_authentication()
                    self.tokens_last_updated = datetime.now()
                headers = {"Authorization": f"Bearer {self.access_token}"}
            async with self.session.get(url, headers=headers, params=payload) as response:
                res = await response.json()
                return res['result']
        except aiohttp.ClientError as e:
            logging.error("Error making GET request to the Deribit API: %s", e)

    async def close(self):
        """Close the HTTP session"""
        try:
            await self.session.close()
            logging.info("HTTP session closed.")
        except aiohttp.ClientError as e:
            logging.error("Error closing the HTTP session: %s", e)


async def main():
    """Main function to test the Deribit API client"""
    try:
        deribit = DeribitClient()
        await deribit.authenticate()
        start = datetime.now()
        print(start)
        while True:
            data = await deribit.get("private/get_account_summary", {"currency": "BTC"})
            print(data['options_vega'])
            end = datetime.now()
            elapsed = (end - start).total_seconds() / 60
            print(f"Elapsed time: {round(elapsed, 2)} minutes")
            await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Exiting with grace")
    finally:
        await deribit.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
