import requests


class EODData:

    def __init__(self, base_url, api_key, exchange, fmt):
        self.session = requests.Session()
        self.base_url = base_url
        self.api_key = api_key
        self.exchange = exchange
        self.fmt = fmt

    def get_candles(self, ticker, exchange, interval, fmt):
        endpoint = "eod" if interval in ["d", "w", "m"] else "intraday"
        params = {
            "period" if endpoint == "eod" else "interval": interval,
            "fmt": fmt,
            "api_token": self.api_key,
        }

        url = f"{self.base_url}/{endpoint}/{ticker}.{exchange}"
        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.json()
