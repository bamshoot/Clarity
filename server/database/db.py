import duckdb
from contextlib import contextmanager


class DB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DB, cls).__new__(cls)
            cls._instance.con = duckdb.connect("./database/clarity.db")
        return cls._instance

    def execute(self, query: str):
        return self.con.sql(query)

    @contextmanager
    def get_connection(self):
        yield self.con

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
        self.close()
