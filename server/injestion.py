import duckdb
from config.config import Config


class Injestion:
    def __init__(self):
        self.con = duckdb.connect("./database/clarity.db")
        self.config = Config()
        print(self.config.EOD_INSTRUMENTS)

    def injest_eod_data(self):
        with duckdb.connect("./database/clarity.db") as con:
            for instrument in self.config.EOD_INSTRUMENTS["cross_rates"]:
                for period in self.config.EOD_INSTRUMENTS["periods"]:
                    file_path = (
                        f"/home/bamshoot/Dev/Clarity/server/data/EOD/"
                        f"{instrument}_{period}.parquet"
                    )
                    con.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {instrument}_{period} AS
                        SELECT * FROM parquet_scan('{file_path}')
                    """
                    )

    def show_tables(self):
        return self.con.sql("SHOW TABLES").fetchall()


injestion = Injestion()
injestion.injest_eod_data()
print(injestion.show_tables())


# with duckdb.connect("./database/clarity.db") as con:
#     print(con.sql("SELECT * FROM USDJPY_d"))
