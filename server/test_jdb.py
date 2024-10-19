import asyncio
from services.eod_data import EODData
from config.config import Config
from schemas.EODCandle import EODCandle
import duckdb
import pandas as pd


async def test_eod_data():
    config = Config()
    async with EODData(config.EOD_URL, config.EOD_API_KEY) as eod:
        candles = await eod.get_candles("EURUSD", "FOREX", "5m", "json")
        return candles


async def test_eod_candle_schema():
    candles_data = await test_eod_data()
    if isinstance(candles_data, list) and candles_data:
        candles = [EODCandle(**candle_data) for candle_data in candles_data]
        print(f"Total candles processed: {len(candles)}")
        return candles
    else:
        print("No candle data received or invalid format")


async def test_insert_candles_duckdb():
    candles = await test_eod_candle_schema()
    df = pd.DataFrame([candle.__dict__ for candle in candles])
    df = df.rename(columns={"datetime_": "datetime", "date_": "date"})
    with duckdb.connect("./database/clarity.db") as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS EURUSD_5m
             AS SELECT * FROM df
             ORDER BY timestamp ASC
        """
        )
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp
             ON EURUSD_5m (timestamp)
        """
        )

        result = con.execute(
            "SELECT * FROM df WHERE timestamp NOT IN (SELECT timestamp FROM EURUSD_5m)"
        )
        print(f"Rows to add: {len(result.fetchall())}")

        con.execute(
            """
            INSERT INTO EURUSD_5m
            SELECT * FROM df
            WHERE timestamp NOT IN (SELECT timestamp FROM EURUSD_5m)
        """
        )


# function to get the final timestamp in the table
def get_final_timestamp(db_path, table_name):
    with duckdb.connect(db_path) as con:
        result = con.sql(f"SELECT MAX(timestamp) FROM {table_name}")
        return result.fetchone()[0]


asyncio.run(test_insert_candles_duckdb())
print(get_final_timestamp("./database/clarity.db", "EURUSD_5m"))
