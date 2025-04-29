from .DataFoundationBuilder import DataFoundationBuilder


class Timestamps(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self.working_table_timestamp = None
        self.working_table_datetime = None
        self.min_timestamp_1h = None
        self.min_timestamp_d = None
        self.min_timestamp_w = None
        self.min_timestamp_m = None
        self.min_datetime_1h = None
        self.min_datetime_d = None
        self.min_datetime_w = None
        self.min_datetime_m = None
        self.min_timeframe_1h = None
        self.min_timeframe_d = None
        self.min_timeframe_w = None
        self.min_timeframe_m = None
        self.min_instrument_1h = None
        self.min_instrument_d = None
        self.min_instrument_w = None
        self.min_instrument_m = None
        self.timestamp_ref_table_1h = None
        self.timestamp_ref_table_d = None
        self.timestamp_ref_table_w = None
        self.timestamp_ref_table_m = None
        self.timestamp_ref_table_1h_timestamp = None
        self.timestamp_ref_table_d_timestamp = None
        self.timestamp_ref_table_w_timestamp = None
        self.timestamp_ref_table_m_timestamp = None

    def set_working_table_timestamp(self):
        self.working_table_timestamp = self.con.sql(
            f"SELECT timestamp FROM {self.working_table_name}").fetchone()[0]

    def set_working_table_datetime(self):
        self.working_table_datetime = self.con.sql(
            f"SELECT datetime FROM {self.working_table_name}").fetchone()[0]

    def _set_min_timestamp(self):
        self.min_timestamp = self.con.sql(
            f"SELECT MIN(timestamp) FROM {self.working_table_name}").fetchone()[0]

    def _set_min_datetime(self):
        self.min_datetime = self.con.sql(
            f"SELECT MIN(datetime) FROM {self.working_table_name}").fetchone()[0]

    def _set_min_timeframe(self):
        self.min_timeframe = self.timeframe

    def _set_min_instrument(self):
        self.min_instrument = self.instrument_name

    def set_timestamp_ref_table(self):

        self.set_working_table_timestamp()
        self.set_working_table_datetime()

        if self.timeframe == "1h":
            if self.min_timestamp_1h is None or \
               self.working_table_timestamp < self.min_timestamp_1h:

                self.min_timestamp_1h = self.con.sql(
                    f"SELECT MIN(timestamp) FROM "
                    f"{self.working_table_name}"
                ).fetchone()[0]
                self.min_datetime_1h = self.working_table_datetime
                self.min_timeframe_1h = self.timeframe
                self.min_instrument_1h = self.instrument_name
                self.timestamp_ref_table_1h = self.working_table_name
                self.timestamp_ref_table_1h_timestamp = self.con.sql(
                    f"SELECT timestamp FROM {self.working_table_name}").fetchall()

        elif self.timeframe == "d":
            if self.min_timestamp_d is None or \
               self.working_table_timestamp < self.min_timestamp_d:

                self.min_timestamp_d = self.con.sql(
                    f"SELECT MIN(timestamp) FROM "
                    f"{self.working_table_name}"
                ).fetchone()[0]
                self.min_datetime_d = self.working_table_datetime
                self.min_timeframe_d = self.timeframe
                self.min_instrument_d = self.instrument_name
                self.timestamp_ref_table_d = self.working_table_name
                self.timestamp_ref_table_d_timestamp = self.con.sql(
                    f"SELECT timestamp FROM {self.working_table_name}")

        elif self.timeframe == "w":
            if self.min_timestamp_w is None or \
               self.working_table_timestamp < self.min_timestamp_w:

                self.min_timestamp_w = self.con.sql(
                    f"SELECT MIN(timestamp) FROM "
                    f"{self.working_table_name}"
                ).fetchone()[0]
                self.min_datetime_w = self.working_table_datetime
                self.min_timeframe_w = self.timeframe
                self.min_instrument_w = self.instrument_name
                self.timestamp_ref_table_w = self.working_table_name
                self.timestamp_ref_table_w_timestamp = self.con.sql(
                    f"SELECT timestamp FROM {self.working_table_name}")

        elif self.timeframe == "m":
            if self.min_timestamp_m is None or \
               self.working_table_timestamp < self.min_timestamp_m:

                self.min_timestamp_m = self.con.sql(
                    f"SELECT MIN(timestamp) FROM "
                    f"{self.working_table_name}"
                ).fetchone()[0]
                self.min_datetime_m = self.working_table_datetime
                self.min_timeframe_m = self.timeframe
                self.min_instrument_m = self.instrument_name
                self.timestamp_ref_table_m = self.working_table_name
                self.timestamp_ref_table_m_timestamp = self.con.sql(
                    f"SELECT timestamp FROM {self.working_table_name}")
