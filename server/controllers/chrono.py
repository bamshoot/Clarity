import pandas as pd


class Chrono:
    async def _partial_candle_insert(self, data, instrument: str, period: str):
        candles = await self._eod_candle_schema(data, instrument, period)
        df = pd.DataFrame([candle.__dict__ for candle in candles])
        df = df.rename(columns={"datetime_": "datetime", "date_": "date"})

        # Register the DataFrame as a temporary table in DuckDB
        with self.db.get_connection() as con:
            con.register("df_temp", df)  # 'df_temp' is the temporary table name

            # Insert new records that do not already exist in the target table
            con.execute(
                f"""
                INSERT INTO {self.prefix}_{instrument}_{period}
                SELECT * FROM df_temp
                WHERE timestamp NOT IN (
                    SELECT timestamp
                    FROM {self.prefix}_{instrument}_{period}
                )
                """
            )

            # Optionally, unregister the temporary table
            con.unregister("df_temp")

            self.logger.logger.info(
                f"Rows added to {self.prefix}_{instrument}_{period}: " f"{con.rowcount}"
            )
