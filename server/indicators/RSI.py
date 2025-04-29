from .DataFoundationBuilder import DataFoundationBuilder


class RSI(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)

    def get_rsi(self, timestamp):
        rsi_data = self.con.sql(f"""
            WITH EURUSD_rsi AS (
                SELECT 'EURUSD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURUSD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            GBPUSD_rsi AS (
                SELECT 'GBPUSD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_GBPUSD_{self.timeframe}
                WHERE timestamp = {timestamp}
            )
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURUSD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPUSD_rsi
        """)

        return rsi_data
