import httpx
import duckdb
from dateutil.relativedelta import relativedelta


class EODData:

    def __init__(self, base_url, api_key, fmt="json"):
        self.client = httpx.AsyncClient()
        self.base_url = base_url
        self.api_key = api_key
        self.con = duckdb.connect("./database/clarity.db")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_candles(self, ticker: str, exchange: str, interval: str, fmt: str):
        endpoint = "eod" if interval in ["d", "w", "m"] else "intraday"
        params = {
            "period" if endpoint == "eod" else "interval": interval,
            "fmt": fmt,
            "api_token": self.api_key,
        }

        url = f"{self.base_url}/{endpoint}/{ticker}.{exchange}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    async def get_latest_candle_in_db(self, ticker: str, exchange: str, interval: str):
        table_name = f"{ticker}_{interval}"
        field = "date" if interval in ["d", "w", "m"] else "timestamp"
        query = f"SELECT MAX({field}) FROM {table_name}"
        return self.con.sql(query).fetchone()[0]

    async def get_candle_plus_one_period(
        self, ticker: str, exchange: str, interval: str
    ):
        latest_candle = await self.get_latest_candle_in_db(ticker, exchange, interval)

        if interval in ["5m", "1h"]:
            # For intraday data, latest_candle is a Unix timestamp
            interval_seconds = {"5m": 300, "1h": 3600}
            return latest_candle + interval_seconds[interval]
        else:
            # For daily, weekly, monthly data, latest_candle is a datetime
            interval_deltas = {
                "d": relativedelta(days=1),
                "w": relativedelta(weeks=1),
                "m": relativedelta(months=1),
            }
            return latest_candle + interval_deltas.get(interval, relativedelta())
