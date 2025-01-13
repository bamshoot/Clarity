from .DataFoundationBuilder import DataFoundationBuilder
import talib as ta


class Trend(DataFoundationBuilder):
    def __init__(self, db_path: str, trends: dict):
        super().__init__(db_path)
        self.params_table_name = "tbl_trend_params"
        self.trend_params = trends

    def reset_trends_table(self):
        self.drop_table(self.params_table_name)
        self.drop_table(self.working_table_name)
        self._create_trend_params_table_from_json()
        self._create_trends_table()

    def _create_trend_params_table_from_json(self):

        self.con.sql(f"""
            CREATE TABLE {self.params_table_name}
            (
                trend_id VARCHAR,
                major_trend_slope_type VARCHAR,
                trend_slope_type VARCHAR,
                run_slope_type VARCHAR,
                major_trend_to_trend VARCHAR,
                trend_to_run VARCHAR,
                status VARCHAR,
                bias VARCHAR,
                objective_status VARCHAR,
                rank_bias VARCHAR,
                rank_major_trend_to_trend VARCHAR,
                rank_trend_to_run VARCHAR,
                overall_rank VARCHAR
            )
        """)

        for trend_id, trend_params in self.trend_params.items():
            self.con.sql(f"""
                INSERT INTO {self.params_table_name}
                VALUES ('{trend_id}',
                        '{trend_params['major_trend_slope_type']}',
                        '{trend_params['trend_slope_type']}',
                        '{trend_params['run_slope_type']}',
                        '{trend_params['major_trend_to_trend']}',
                        '{trend_params['trend_to_run']}',
                        '{trend_params['status']}',
                        '{trend_params['bias']}',
                        '{trend_params['objective_status']}',
                        '{trend_params['rank_bias']}',
                        '{trend_params['rank_major_trend_to_trend']}',
                        '{trend_params['rank_trend_to_run']}',
                        '{trend_params['overall_rank']}')
            """)

    def _create_trends_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
            (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                trend_id VARCHAR,
                major_trend_slope_value DOUBLE,
                trend_slope_value DOUBLE,
                run_slope_value DOUBLE,
                major_trend_slope_type VARCHAR,
                trend_slope_type VARCHAR,
                run_slope_type VARCHAR,
                major_trend_to_trend VARCHAR,
                trend_to_run VARCHAR,
                status VARCHAR,
                bias VARCHAR,
                objective_status VARCHAR,
                rank_bias VARCHAR,
                rank_major_trend_to_trend VARCHAR,
                rank_trend_to_run VARCHAR,
                overall_rank VARCHAR
            )
        """)

    def set_working_table_name(self, working_table_name: str):
        self.working_table_name = working_table_name

    def _append_instrument_trends(self,
                                  trend_id,
                                  major_trend_slope_value,
                                  trend_slope_value,
                                  run_slope_value):
        self.con.sql(f"""
            WITH trend_params AS (
                SELECT major_trend_slope_type, trend_slope_type, run_slope_type,
                       major_trend_to_trend, trend_to_run, status, bias,
                       objective_status, rank_bias, rank_major_trend_to_trend,
                       rank_trend_to_run, overall_rank
                FROM tbl_trend_params
                WHERE trend_id = '{trend_id}'
            )
            INSERT INTO {self.working_table_name}
            SELECT '{self.instrument_name}' as instrument_name,
                   '{self.timeframe}' as timeframe,
                   '{trend_id}' as trend_id,
                   {major_trend_slope_value}, {trend_slope_value}, {run_slope_value},
                   major_trend_slope_type, trend_slope_type, run_slope_type,
                   major_trend_to_trend, trend_to_run, status, bias,
                   objective_status, rank_bias, rank_major_trend_to_trend,
                   rank_trend_to_run, overall_rank
            FROM trend_params
        """)

    def generate_trends(self):

        run_length = 9
        trend_length = 20
        major_trend_length = 50
        run_threshold = 15
        trend_threshold = 5
        major_trend_threshold = 5

        data = self.get_table_from_db(self.source_table_name).fetchnumpy()

        close_prices = data['close']
        high_prices = data['high']
        low_prices = data['low']

        atr = ta.ATR(high_prices, low_prices, close_prices, 14)

        sma_major_trend = ta.SMA(close_prices, major_trend_length)
        sma_trend = ta.SMA(close_prices, trend_length)
        sma_run = ta.SMA(close_prices, run_length)

        slope_major_trend = round((ta.LINEARREG_SLOPE(
            sma_major_trend, 2)[-1]/atr[-1])*100, 2)
        slope_trend = round((ta.LINEARREG_SLOPE(
            sma_trend, 2)[-1]/atr[-1])*100, 2)
        slope_run = round((ta.LINEARREG_SLOPE(
            sma_run, 2)[-1]/atr[-1])*100, 2)

        major_trend_slope_type = None
        trend_slope_type = None
        run_slope_type = None

        if slope_major_trend > major_trend_threshold:
            major_trend_slope_type = "Up"
        elif slope_major_trend < -major_trend_threshold:
            major_trend_slope_type = "Down"

        if slope_trend > trend_threshold:
            trend_slope_type = "Up"
        elif slope_trend < -trend_threshold:
            trend_slope_type = "Down"

        if slope_run > run_threshold:
            run_slope_type = "Up"
        elif slope_run < -run_threshold:
            run_slope_type = "Down"

        trend_id = f"{major_trend_slope_type}{trend_slope_type}{run_slope_type}"

        self._append_instrument_trends(trend_id,
                                       slope_major_trend,
                                       slope_trend,
                                       slope_run)
