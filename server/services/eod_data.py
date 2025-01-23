import httpx


class EODData:

    def __init__(self, base_url: str, api_key: str, db_connection=None):
        self.client = httpx.AsyncClient()
        self.base_url = base_url
        self.api_key = api_key
        self.con = db_connection

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_candles(
        self,
        ticker: str,
        exchange: str,
        interval: str,
        fmt: str = "json",
    ):
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

    async def get_candles_with_from(
        self,
        ticker: str,
        exchange: str,
        interval: str,
        db_from: str,
        fmt: str = "json",
    ):
        endpoint = "eod" if interval in ["d", "w", "m"] else "intraday"
        params = {
            "period" if endpoint == "eod" else "interval": interval,
            "from": db_from,
            "fmt": fmt,
            "api_token": self.api_key,
        }

        url = f"{self.base_url}/{endpoint}/{ticker}.{exchange}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    async def get_last_price(self,
                             ticker: str,
                             exchange: str,
                             fmt: str = "json"):
        endpoint = "real-time"
        params = {
            "fmt": fmt,
            "api_token": self.api_key,
        }
        url = f"{self.base_url}/{endpoint}/{ticker}.{exchange}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    async def get_latest_candle_in_db(
        self, prefix: str, ticker: str, exchange: str, interval: str
    ):
        table_name = f"{prefix}_{ticker}_{interval}"
        if interval in ["d", "w", "m"]:
            query = f"SELECT MAX(CAST(date AS DATE)) FROM {table_name}"
        else:
            query = f"SELECT MAX(timestamp) FROM {table_name}"
        return self.con.sql(query).fetchone()[0]
