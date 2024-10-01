import asyncio
import os
import json
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
from utils.logger import Logger
from config.config import Config

config = Config()


class Chrono:
    def __init__(self, name: str, interval: int = 10):
        """
        Asynchronous Chrono class for periodic tasks.

        :param name: Name of the Chrono instance.
        :param interval: Time interval between executions in seconds.
        """
        self.name = name
        self.interval = interval
        self.logger = Logger(self.name, mode="a")
        self._stop_event = asyncio.Event()
        self._task = None

    async def _run(self):
        """Asynchronous loop that performs the periodic task."""
        self.logger.logger.info(
            f"{self.name} _run started with interval {self.interval} seconds."
        )
        while not self._stop_event.is_set():
            start_time = asyncio.get_event_loop().time()
            self.logger.logger.debug(f"{self.name} executing task.")
            try:
                await self._execute_task()
            except Exception as e:
                self.logger.logger.error(
                    f"Error during {self._execute_task.__name__}: {e}"
                )
            elapsed = asyncio.get_event_loop().time() - start_time
            sleep_time = self.interval - elapsed
            if sleep_time > 0:
                self.logger.logger.debug(
                    f"{self.name} sleeping for {sleep_time:.2f} seconds."
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_time)
                except asyncio.TimeoutError:
                    pass
            else:
                self.logger.logger.warning(
                    f"{self.name} task execution took longer ({elapsed:.2f} seconds) "
                    f"than the interval ({self.interval} seconds)."
                )

    async def _execute_task(self):
        """
        Placeholder for the task to be executed periodically.
        Override this method in subclasses.
        """
        pass

    async def start(self):
        """Starts the Chrono's asynchronous task."""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run())
            self.logger.logger.info(f"{self.name} started.")
        else:
            self.logger.logger.warning(f"{self.name} is already running.")

    async def stop(self, timeout: int = 5):
        """
        Stops the Chrono's asynchronous task.

        :param timeout: Time to wait for the task to finish.
        """
        if self._task and not self._task.done():
            self._stop_event.set()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
                self.logger.logger.info(f"{self.name} stopped gracefully.")
            except asyncio.TimeoutError:
                self.logger.logger.warning(
                    f"{self.name} did not stop within the timeout period."
                )
        else:
            self.logger.logger.warning(f"{self.name} is not running.")

    def is_running(self) -> bool:
        """Checks if the Chrono's task is currently running."""
        return self._task is not None and not self._task.done()


class DataCollectionChrono(Chrono):
    def __init__(
        self, data_service, interval: int = 300, max_concurrent_requests: int = 10
    ):
        """
        Asynchronous DataCollectionChrono for collecting EOD data.

        :param data_service: Service to fetch candle data.
        :param interval: Time interval between data collection cycles in seconds.
        :param max_concurrent_requests: Maximum number of concurrent HTTP requests.
        """
        super().__init__(name="data_collection_chrono", interval=interval)
        self.data_service = data_service
        self.instruments = config.EOD_INSTRUMENTS["cross_rates"]
        self.periods = config.EOD_INSTRUMENTS["periods"]
        self.cross_rates_periods = [
            (instrument, period)
            for instrument in self.instruments
            for period in self.periods
        ]
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _execute_task(self):
        """Overrides the base method to perform data collection."""
        self.logger.logger.info("Starting data collection task.")
        os.makedirs("data/EOD", exist_ok=True)
        tasks = [
            self._fetch_and_save(instrument, period)
            for instrument, period in self.cross_rates_periods
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.logger.error(f"Error in data collection task: {result}")
        self.logger.logger.info("Data collection task completed.")

    async def _fetch_and_save(self, instrument: str, period: str):
        """
        Fetches candle data and saves it to a Parquet file.

        :param instrument: The financial instrument to fetch data for.
        :param period: The time period for the candle data.
        """
        async with self.semaphore:
            try:
                raw_data = await self.data_service.get_candles(
                    instrument,
                    "FOREX",
                    period,
                    "json",
                )
                if not raw_data:
                    self.logger.logger.warning(
                        f"No data fetched for {instrument} on the {period} period."
                    )
                else:
                    file_path = f"data/EOD/{instrument}_{period}.parquet"
                    self._save_json_to_parquet(raw_data, file_path)
            except httpx.HTTPStatusError as he:
                self.logger.logger.error(f"HTTP Error for {instrument} {period}: {he}")
            except Exception as e:
                self.logger.logger.error(
                    "Unexpected error in data collection for %s %s: %s",
                    instrument,
                    period,
                    e,
                )

    def _save_json_to_parquet(self, raw_data, file_path: str):
        """
        Saves JSON data to a Parquet file.

        :param raw_data: JSON data to save.
        :param file_path: Path to the Parquet file.
        """
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
