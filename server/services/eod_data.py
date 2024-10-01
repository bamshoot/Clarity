import httpx


class EODData:

    def __init__(self, base_url, api_key, fmt="json"):
        self.client = httpx.AsyncClient()
        self.base_url = base_url
        self.api_key = api_key

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
