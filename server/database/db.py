import duckdb
from contextlib import contextmanager
# import pprint


class DB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DB, cls).__new__(cls)
            cls._instance.con = None
        return cls._instance

    def connect(self):
        if self.con is None:
            self.con = duckdb.connect("./database/clarity.db")

    def execute(self, query: str):
        self.connect()
        return self.con.execute(query)

    @contextmanager
    def get_connection(self):
        self.connect()
        try:
            yield self.con
        finally:
            pass  # We don't close the connection here anymore

    def close(self):
        if self.con:
            self.con.close()
        self.con = None
        DB._instance = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"An error occurred: {exc_val}")
        # We don't close the connection here anymore
        pass

    def table_exists(self, table_name: str) -> bool:
        self.connect()
        result = self.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = '{table_name}'
            """
        )
        exists = len(result.fetchall()) > 0
        return exists


def list_tables(db_path):
    with duckdb.connect(db_path) as con:
        return con.sql("SHOW TABLES").fetchall()


def drop_tables(db_path):
    with duckdb.connect(db_path) as con:
        tables = con.sql("SHOW TABLES").fetchall()
        for table in tables:
            con.sql(f"DROP TABLE IF EXISTS {table[0]}")


def get_table(db_path, table_name):
    with duckdb.connect(db_path) as con:
        print(con.sql(f"SELECT * FROM {table_name}"))


def drop_table(db_path, table_name):
    with duckdb.connect(db_path) as con:
        con.sql(f"DROP TABLE IF EXISTS {table_name}")


# pprint.pprint(list_tables("./database/clarity.db"))
# drop_tables("./database/clarity.db")
# drop_table("./database/clarity.db", "tbl_EOD_EURUSD_1h_f2_k10_temp")

# get_table("./database/clarity.db", "tbl_EOD_AUDCAD_1h")
# get_table("./database/clarity.db", "tbl_EOD_AUDCAD_5m")
