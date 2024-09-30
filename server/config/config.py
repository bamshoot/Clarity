import os
from dotenv import load_dotenv
import json
from typing import Dict, Any


class Config:
    def __init__(self):
        load_dotenv()
        self._config: Dict[str, Any] = {}
        self._load_env_vars()
        self._load_json_files()

    def _load_env_vars(self):
        self._config.update(
            {
                "OANDA_API_KEY": os.getenv("OANDA_API_KEY"),
                "OANDA_ACCOUNT_ID": os.getenv("OANDA_ACCOUNT_ID"),
                "OANDA_URL": os.getenv("OANDA_URL"),
                "EOD_API_KEY": os.getenv("EOD_API_KEY"),
                "EOD_URL": os.getenv("EOD_URL"),
            }
        )

    def _load_json_files(self):
        json_files = {
            "OANDA_INSTRUMENTS": "config/settings/oanda_instruments.json",
            "OANDA_TRADE": "config/settings/oanda_trade.json",
            "EOD_INSTRUMENTS": "config/settings/eod_instruments.json",
        }
        for key, file_path in json_files.items():
            with open(file_path, "r") as f:
                self._config[key] = json.load(f)

    @property
    def OANDA_SECURE_HEADER(self):
        return {
            "Authorization": f"Bearer {self._config['OANDA_API_KEY']}",
            "Content-Type": "application/json",
        }

    def __getattr__(self, name):
        return self._config.get(name)

    # Constants
    SELL = -1
    BUY = 1
    NONE = 0
    FRACTAL_SIZE = 2


# Create a global instance of the config
config = Config()
