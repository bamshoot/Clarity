import duckdb
# import pprint


class DB:
    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DB, cls).__new__(cls)
        return cls._instance

    def connect(self):
        if DB._connection is None:
            DB._connection = duckdb.connect("./database/clarity.db")

    def execute(self, query: str):
        try:
            self.connect()
            return DB._connection.execute(query)
        except Exception:
            DB._connection = None
            self.connect()
            return DB._connection.execute(query)

    def get_connection(self):
        try:
            self.connect()
            return DB._connection
        except Exception:
            DB._connection = None
            self.connect()
            return DB._connection

    def close(self):
        if DB._connection:
            DB._connection.close()
            DB._connection = None
        DB._instance = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"An error occurred: {exc_val}")
        # Don't close the connection here
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
