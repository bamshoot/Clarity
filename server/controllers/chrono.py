import asyncio
import pandas as pd
from utils.logger import Logger
from config.config import Config
from database.db import DB
from schemas.EODCandle import EODCandle

config = Config()


class Chrono:
    def __init__(self, name: str, interval: int = 10, db: DB = None):
        """
        Asynchronous Chrono class for periodic tasks.

        :param name: Name of the Chrono instance.
        :param interval: Time interval between executions in seconds.
        """
        self.name = name
        self.interval = interval
        self.db = db
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


class EODDataCollectionChrono(Chrono):
    def __init__(
        self, data_service, interval: int, max_concurrent_requests: int, db: DB
    ):
        """
        Asynchronous DataCollectionChrono for collecting EOD data.

        :param data_service: Service to fetch candle data.
        :param interval: Time interval between data collection cycles in seconds.
        :param max_concurrent_requests: Maximum number of concurrent HTTP requests.
        """
        super().__init__(name="data_collection_chrono", interval=interval, db=db)
        self.data_service = data_service
        self.instruments = config.EOD_INSTRUMENTS["cross_rates"]
        self.periods = config.EOD_INSTRUMENTS["periods"]
        self.prefix = "tbl_EOD"
        self.cross_rates_periods = [
            (instrument, period)
            for instrument in self.instruments
            for period in self.periods
        ]
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _get_candles(self, instrument: str, period: str):
        return await self.data_service.get_candles(
            instrument, "FOREX", period
        )

    async def _get_candles_with_from(self, instrument: str, period: str, db_from: str):
        return await self.data_service.get_candles_with_from(
            instrument, "FOREX", period, db_from
        )

    async def _eod_candle_schema(self, data, instrument: str, period: str):
        if isinstance(data, list) and data:
            candles = [EODCandle(**candle_data) for candle_data in data]
            self.logger.logger.info(
                f"Total candles from API: {len(candles)} for {instrument} {period}"
            )
            return candles
        return []

    async def _full_candle_insert(self, instrument: str, period: str):
        data = await self._get_candles(instrument, period)
        candles = await self._eod_candle_schema(data, instrument, period)
        df = pd.DataFrame([candle.__dict__ for candle in candles])
        df = df.rename(columns={"datetime_": "datetime", "date_": "date"})

        with self.db.get_connection() as con:
            con.register("df_temp", df)

            con.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.prefix}_{instrument}_{period}
                AS SELECT * FROM df_temp
                """
            )

            con.execute(
                f"""CREATE INDEX IF NOT EXISTS idx_timestamp
                     ON {self.prefix}_{instrument}_{period} (timestamp)"""
            )

            con.unregister("df_temp")

    async def _partial_candle_insert(self, instrument: str, period: str):
        db_from = await self.data_service.get_latest_candle_in_db(
            self.prefix, instrument, "FOREX", period
        )

        data = await self._get_candles_with_from(instrument, period, db_from)

        candles = await self._eod_candle_schema(data, instrument, period)
        df = pd.DataFrame([candle.__dict__ for candle in candles])
        df = df.rename(columns={"datetime_": "datetime", "date_": "date"})

        if period in ["5m", "1h"]:
            df = df[df["timestamp"] > db_from]
        else:
            df = df[df["date"] > db_from]

        new_rows = len(df)

        if new_rows > 0:
            with self.db.get_connection() as con:
                con.register("df_temp", df)
                con.execute(f"""
                    INSERT INTO {self.prefix}_{instrument}_{period}
                    SELECT *
                    FROM df_temp
                    WHERE timestamp NOT IN (
                        SELECT timestamp
                        FROM {self.prefix}_{instrument}_{period}
                    )
                """)

                con.unregister("df_temp")

                self.logger.logger.info(
                    f"Rows added to {self.prefix}_{instrument}_{period}: {new_rows}"
                )
        else:
            self.logger.logger.info(
                f"No new rows to add to {self.prefix}_{instrument}_{period}"
            )

    async def _execute_task(self):
        self.logger.logger.info("Starting data collection task.")

        for instrument, period in self.cross_rates_periods:
            table_name = f"{self.prefix}_{instrument}_{period}"
            try:
                table_exists = self.db.table_exists(table_name)

                if not table_exists:
                    self.logger.logger.info(f"Creating new table: {table_name}")
                    await self._full_candle_insert(instrument, period)

                else:
                    await self._partial_candle_insert(instrument, period)

            except Exception as e:
                self.logger.logger.error(f"Error processing {table_name}: {str(e)}")
