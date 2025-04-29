from .DataFoundationBuilder import DataFoundationBuilder


class RSI(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self.rsi_data = None

    def build_rsi_data(self, timestamp):
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
            ),
            USDJPY_rsi AS (
                SELECT 'USDJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_USDJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            AUDUSD_rsi AS (
                SELECT 'AUDUSD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_AUDUSD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            USDCHF_rsi AS (
                SELECT 'USDCHF' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_USDCHF_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            USDCAD_rsi AS (
                SELECT 'USDCAD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_USDCAD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            NZDUSD_rsi AS (
                SELECT 'NZDUSD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_NZDUSD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            EURGBP_rsi AS (
                SELECT 'EURGBP' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURGBP_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            EURJPY_rsi AS (
                SELECT 'EURJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            EURAUD_rsi AS (
                SELECT 'EURAUD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURAUD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            EURCAD_rsi AS (
                SELECT 'EURCAD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURCAD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            EURCHF_rsi AS (
                SELECT 'EURCHF' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURCHF_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            EURNZD_rsi AS (
                SELECT 'EURNZD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_EURNZD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            GBPJPY_rsi AS (
                SELECT 'GBPJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_GBPJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            GBPAUD_rsi AS (
                SELECT 'GBPAUD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_GBPAUD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            GBPCHF_rsi AS (
                SELECT 'GBPCHF' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_GBPCHF_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            GBPCAD_rsi AS (
                SELECT 'GBPCAD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_GBPCAD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            GBPNZD_rsi AS (
                SELECT 'GBPNZD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_GBPNZD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            AUDJPY_rsi AS (
                SELECT 'AUDJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_AUDJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            AUDCHF_rsi AS (
                SELECT 'AUDCHF' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_AUDCHF_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            AUDCAD_rsi AS (
                SELECT 'AUDCAD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_AUDCAD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            AUDNZD_rsi AS (
                SELECT 'AUDNZD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_AUDNZD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            CHFJPY_rsi AS (
                SELECT 'CHFJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_CHFJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            CADJPY_rsi AS (
                SELECT 'CADJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_CADJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            NZDJPY_rsi AS (
                SELECT 'NZDJPY' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_NZDJPY_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            CADCHF_rsi AS (
                SELECT 'CADCHF' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_CADCHF_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            NZDCAD_rsi AS (
                SELECT 'NZDCAD' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_NZDCAD_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),
            NZDCHF_rsi AS (
                SELECT 'NZDCHF' as instrument, '{self.timeframe}' as timeframe,
                       timestamp, rsi14
                FROM tbl_{self.data_source}_NZDCHF_{self.timeframe}
                WHERE timestamp = {timestamp}
            ),

            rsi_data AS (
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURUSD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPUSD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM USDJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM AUDUSD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM USDCHF_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM USDCAD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM NZDUSD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURGBP_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURAUD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURCAD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURCHF_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM EURNZD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPAUD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPCHF_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPCAD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM GBPNZD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM AUDJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM AUDCHF_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM AUDCAD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM AUDNZD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM CHFJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM CADJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM NZDJPY_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM CADCHF_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM NZDCAD_rsi
            UNION ALL
            SELECT instrument, timeframe, timestamp, rsi14
            FROM NZDCHF_rsi
            )
            SELECT *, abs(rsi14 - 50) as rsi_diff,
            DENSE_RANK() OVER (
                PARTITION BY timeframe
                ORDER BY rsi_diff DESC
            ) as rsi_rank,
            CASE
                WHEN rsi_diff >= 10 AND rsi14 < 50 THEN 'buy'
                WHEN rsi_diff >= 10 AND rsi14 > 50 THEN 'sell'
                ELSE 'neutral'
            END as rsi_status
            FROM rsi_data
            ORDER BY rsi_diff DESC
        """)

        self.rsi_data = rsi_data

    def get_rsi_data(self):

        return self.rsi_data
