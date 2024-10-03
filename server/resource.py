from database.db import DB


def williams_fractal(
    db: DB,
    table: str,
    period: int = 2,
    data_point: str = "close",
    column_name: str = "date",
):
    sql_query = f"""
        WITH data AS (
            SELECT *,
                MAX({data_point}) OVER (
                    ORDER BY {column_name}
                    ROWS BETWEEN {period} PRECEDING AND {period} FOLLOWING
                ) AS close_max,
                MIN({data_point}) OVER (
                    ORDER BY {column_name}
                    ROWS BETWEEN {period} PRECEDING AND {period} FOLLOWING
                ) AS close_min
            FROM {table}
        )
        SELECT
            *,
            CASE WHEN close = close_max THEN close ELSE NULL END AS uf,
            CASE WHEN close = close_min THEN close ELSE NULL END AS lf
        FROM data
        ORDER BY {column_name};
    """
    return db.execute(sql_query)
