import duckdb
from contextlib import contextmanager


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
