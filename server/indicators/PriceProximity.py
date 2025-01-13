from server.indicators.DataFoundationBuilder import DataFoundationBuilder
import talib as ta


class PriceProximity(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self.exchange = None
        self.eod_data_service = None

    def reset_price_proximity_table(self):
        self.drop_table(self.working_table_name)
        self._create_price_proximity_table()

    def set_exchange(self, exchange: str):
        self.exchange = exchange

    def set_data_service(self, eod_data_service):
        self.eod_data_service = eod_data_service

    def _create_price_proximity_table(self):

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
            AS SELECT * FROM {self.source_table_name}
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name} ADD COLUMN lst_price_timestamp BIGINT
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name} ADD COLUMN lst_price DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name} ADD COLUMN lst_price_cent_dist DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name} ADD COLUMN atr DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name} ADD COLUMN proximity DOUBLE
        """)

    async def _get_last_price(self):
        last_price = await self.eod_data_service.get_last_price(
            self.instrument_name,
            self.exchange)

        return last_price["timestamp"], last_price["close"]

    def _get_atr(self):
        data = self.get_table_from_db(self.source_table_name).fetchnumpy()
        atr = ta.ATR(data["high"], data["low"], data["close"], 14)
        return atr[-1]

    async def append_price_atr(self):

        timestamp, price = await self._get_last_price()
        atr = self._get_atr()

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET lst_price_timestamp = {timestamp},
                lst_price = {price},
                atr = {atr}
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
        """)

    def calculate_price_proximity(self):

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET lst_price_cent_dist = lst_price - cent,
                proximity = lst_price_cent_dist / atr
        """)
