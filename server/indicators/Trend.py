import talib as ta
import numpy as np

from .DataFoundationBuilder import DataFoundationBuilder


class Trend(DataFoundationBuilder):
    def __init__(self, db_connection,
                 trend_length_threshold: dict,
                 trends_status_rank: dict):
        super().__init__(db_connection)
        self.params_table_name = "tbl_trend_params"
        self.trend_length_threshold = trend_length_threshold
        self.trends_status_rank = trends_status_rank

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

        for trend_id, trend_params in self.trends_status_rank.items():
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

    def reset_trends_fields_to_table(self):
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS major_trend_slope_value
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS trend_slope_value
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS run_slope_value
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS trend_slope_value
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS run_slope_value
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS major_trend_slope_type
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS trend_slope_type
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS run_slope_type
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS major_trend_to_trend
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS trend_to_run
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS status
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS bias
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS objective_status
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS rank_bias
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS rank_major_trend_to_trend
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS rank_trend_to_run
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            DROP COLUMN IF EXISTS overall_rank
        """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS major_trend_slope_value DOUBLE
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS trend_slope_value DOUBLE
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS run_slope_value DOUBLE
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS run_slope_value DOUBLE
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS major_trend_slope_type VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS trend_slope_type VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS run_slope_type VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS major_trend_to_trend VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS trend_to_run VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS status VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS bias VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS objective_status VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS rank_bias VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS rank_major_trend_to_trend VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS rank_trend_to_run VARCHAR
            """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS overall_rank VARCHAR
        """)

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

    def get_table_from_db(self, table_name, timestamp, timestamps_back=2):

        return self.con.sql(f"""
            WITH timestamps AS (
                SELECT timestamp FROM {table_name}
                WHERE timestamp < '{timestamp}'
                ORDER BY timestamp DESC
                LIMIT {timestamps_back}
            )
            SELECT * FROM {table_name}
            WHERE timestamp IN (SELECT timestamp FROM timestamps)
        """)


    def generate_trends(self, timestamp):

        run_length = self.trend_length_threshold["run_length"]
        trend_length = self.trend_length_threshold["trend_length"]
        major_trend_length = self.trend_length_threshold["major_trend_length"]
        run_threshold = self.trend_length_threshold["run_threshold"]
        trend_threshold = self.trend_length_threshold["trend_threshold"]
        major_trend_threshold = self.trend_length_threshold["major_trend_threshold"]

        data = self.get_table_from_db(self.working_table_name, timestamp, 2)

        atr = np.array(
            self.con.sql(f"""
                SELECT atr14 FROM {self.working_table_name}
                WHERE timestamp = '{timestamp}'
            """).fetchone()[0]
        )

        sma_major_trend = np.array(data['sma9'].fetchall()).flatten()
        sma_trend = np.array(data['sma20'].fetchall()).flatten()
        sma_run = np.array(data['sma50'].fetchall()).flatten()

        if len(sma_major_trend) < 2 or len(sma_trend) < 2 or len(sma_run) < 2:
            return

        slope_major_trend = ((ta.LINEARREG_SLOPE(
            sma_major_trend, 2)/atr)*100)[-1]
        slope_trend = ((ta.LINEARREG_SLOPE(
            sma_trend, 2)/atr)*100)[-1]
        slope_run = ((ta.LINEARREG_SLOPE(
            sma_run, 2)/atr)*100)[-1]

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

        # # self._append_instrument_trends(trend_id,
        # #                                slope_major_trend,
        # #                                slope_trend,
        # #                                slope_run)

        print(trend_id, slope_major_trend, slope_trend, slope_run)
