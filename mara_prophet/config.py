"""
Configures mara-prophet KPI-forecasting module
"""


def db_alias():
    """The alias of the database that should be used when not specified otherwise"""
    return 'dwh-etl'


def forecast_table_name():
    """An ETL integrated table name (str) for storing the forecasts.
    If None then no ETL-integration will take place"""
    return None


def forecasts() -> []:
    """A list with the forecast objects (and their configuration) to be run

    Example:

        [
            Forecast(
            metric_name='Metric name',
            number_of_days=120,
            time_series_query=mara_prophet.sql.build_time_series_sql_query(
                schema_name='schema',
                table_name='table',
                ds_column='date',
                y_expression='sum(metric_field)',
                where_condition='date >= \'2018-01-01\'::DATE'),
            growth='linear',
            holidays=None,
            seasonality=Seasonality(),
            changepoint=Changepoint())
        ]

    """
    return []
