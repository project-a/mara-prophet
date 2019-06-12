"""Helper methods to generate PostgreSQL queries for Mara Prophet"""


def build_time_series_sql_query(schema_name: str, table_name: str, ds_column: str, y_expression: str,
                                where_condition: str = None):
    return f"""
SELECT * FROM (
    SELECT {ds_column} AS ds,
    {y_expression} AS y
    FROM {schema_name}.{table_name} 
    WHERE {where_condition if where_condition is not None else '1=1'}
    GROUP BY 1
    ORDER BY 1 DESC
) AS t
WHERE y != 0
"""
