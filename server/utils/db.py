import duckdb


def list_tables(db_path):
    with duckdb.connect(db_path) as con:
        return con.sql("SHOW TABLES").fetchall()


def drop_tables(db_path):
    with duckdb.connect(db_path) as con:
        tables = con.sql("SHOW TABLES").fetchall()
        for table in tables:
            con.sql(f"DROP TABLE IF EXISTS {table[0]}")


# print(list_tables("./database/clarity.db"))
drop_tables("./database/clarity.db")
