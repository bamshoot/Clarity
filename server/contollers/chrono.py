import time
import threading
import os
import httpx
import asyncio
import pyarrow as pa
import pyarrow.parquet as pq
from utils.logger import Logger
import json
from config.config import Config

config = Config()


class Chrono:
    def __init__(self, name, interval=10):
        self.name = name
        self.interval = interval
        self.logger = Logger(self.name, mode="a")
        self._stop_event = threading.Event()
        self.thread = None

    def _run(self):
        while not self._stop_event.is_set():
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.logger.logger.info(f"Current time: {current_time}")
            time.sleep(self.interval)

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.start()
        else:
            self.logger.logger.warning(f"{self.name} is already running")

    def stop(self, timeout=5):
        if self.thread and self.thread.is_alive():
            self._stop_event.set()
            self.thread.join(timeout)
            if self.thread.is_alive():
                self.logger.logger.warning(
                    f"{self.name} did not stop within the timeout period."
                )
        else:
            self.logger.logger.warning(f"{self.name} is not running")

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()


class DataCollectionChrono(Chrono):
    def __init__(self, data_service, interval=300):
        super().__init__(name="data_collection_chrono", interval=interval)
        self.data_service = data_service
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.instruments = config.EOD_INSTRUMENTS["cross_rates"]
        self.periods = config.EOD_INSTRUMENTS["periods"]
        self.cross_rates_periods = [
            (instrument, period)
            for instrument in self.instruments
            for period in self.periods
        ]

    def _save_json_to_parquet(self, raw_data, file_path):
        try:
            if isinstance(raw_data, dict):
                raw_data = [raw_data]
            elif isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
                if isinstance(raw_data, dict):
                    raw_data = [raw_data]

            table = pa.Table.from_pylist(raw_data)
            pq.write_table(table, file_path)
            self.logger.logger.info(f"Data saved to {file_path}")
        except json.JSONDecodeError as je:
            self.logger.logger.error(f"JSON Decode Error: {je}")
        except pa.lib.ArrowInvalid as ae:
            self.logger.logger.error(f"Arrow Invalid Error: {ae}")
        except Exception as e:
            self.logger.logger.error(f"Failed to save data: {e}")

    def _run(self):
        os.makedirs("data/EOD", exist_ok=True)

        while not self._stop_event.is_set():
            try:
                for instrument in self.instruments:
                    for period in self.periods:
                        raw_data = self.loop.run_until_complete(
                            self.data_service.get_candles(
                                instrument,
                                "FOREX",
                                period,
                                "json",
                            )
                        )
                        if not raw_data:
                            self.logger.logger.warning(
                                "No data fetched for {} on the {} period.".format(
                                    instrument, period
                                )
                            )
                        else:
                            file_path = f"data/EOD/{instrument}_{period}.parquet"
                            self._save_json_to_parquet(raw_data, file_path)

            except httpx.HTTPStatusError as he:
                self.logger.logger.error(f"HTTP Error: {he}")
            except Exception as e:
                self.logger.logger.error(f"Unexpected error in data collection: {e}")

            for _ in range(self.interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
