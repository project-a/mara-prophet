import logging
import sys
import json

import mara_db.postgresql
import mara_db.auto_migration
import mara_prophet.config
import numpy as np
import pandas as pd

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import pickle
from psycopg2 import Binary
import datetime

Base = declarative_base()

import matplotlib

matplotlib.use('agg')
from fbprophet import Prophet, forecaster


class ForecastBase(Base):
    """
    Stores all time-series models and the forecasts dataframe in order to allow analysing the performance of the
    prediction models and asynchronously rendering forecasts plots.
    Running that data (sql queries, parameters) through the browser would pose security threats.
    """
    __tablename__ = 'forecasts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    metric_name = sqlalchemy.Column(sqlalchemy.TEXT, nullable=False)
    forecast_ts = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), nullable=False)
    model = sqlalchemy.Column(sqlalchemy.LargeBinary)
    forecasts_df = sqlalchemy.Column(sqlalchemy.LargeBinary)
    source_df = sqlalchemy.Column(sqlalchemy.LargeBinary)
    hyper_parameters = sqlalchemy.Column(JSONB)

    __table_args__ = (sqlalchemy.UniqueConstraint('metric_name', 'forecast_ts', name='forecasts_uk'),)


class Seasonality:
    def __init__(self, seasonality_mode='additive', seasonality_prior_scale=10.0, yearly_seasonality='auto',
                 weekly_seasonality='auto', daily_seasonality='auto'):
        self.seasonality_mode = seasonality_mode
        self.seasonality_prior_scale = seasonality_prior_scale
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality


class Changepoint:
    def __init__(self, changepoints=None, n_changepoints=25, changepoint_range=0.8, changepoint_prior_scale=0.05):
        self.changepoints = changepoints
        self.n_changepoints = n_changepoints
        self.changepoint_range = changepoint_range
        self.changepoint_prior_scale = changepoint_prior_scale


class Forecast:
    def __init__(self, metric_name: str, number_of_days: int, time_series_query: str,
                 growth: str = 'linear', holidays: pd.DataFrame = None, seasonality: Seasonality = Seasonality(),
                 changepoint: Changepoint = Changepoint()) -> None:
        self.metric_name = metric_name
        self.number_of_days = number_of_days
        self.time_series_query = time_series_query
        self.growth = growth
        self.holidays = holidays
        self.seasonality = seasonality
        self.changepoint = changepoint

    def read_data(self):
        """
        Read and log transform historic data
        """
        with mara_db.postgresql.postgres_cursor_context(mara_prophet.config.db_alias()) as cursor:
            cursor.execute(f'''{self.time_series_query};''')
            df = pd.DataFrame(cursor.fetchall(), columns=['ds', 'y'])

        return df

    def insert_into_table(self, forecast):
        """
        Insert historic and predict tables into forecast table
        """
        for index, row in forecast.iterrows():
            with mara_db.postgresql.postgres_cursor_context(mara_prophet.config.db_alias()) as cursor:
                cursor.execute(
                    f"INSERT INTO {mara_prophet.config.forecast_table_name()} VALUES ({'%s, %s, %s, %s, %s'})",
                    (row['ds'], self.metric_name, row['yhat'], row['yhat_lower'], row['yhat_upper']))

    def forecast_metric(self):
        """
        Forecast the metric for the next {number_of_days} days
        """
        np.warnings.filterwarnings('ignore')

        logging_handler = logging.StreamHandler(sys.stdout)
        logging_handler.setLevel(logging.DEBUG)
        forecaster.logger.addHandler(logging_handler)

        df = self.read_data()

        df['y'] = np.log(df['y'])

        m = Prophet(
            growth=self.growth,
            holidays=self.holidays,
            seasonality_mode=self.seasonality.seasonality_mode,
            seasonality_prior_scale=self.seasonality.seasonality_prior_scale,
            yearly_seasonality=self.seasonality.yearly_seasonality,
            weekly_seasonality=self.seasonality.weekly_seasonality,
            daily_seasonality=self.seasonality.daily_seasonality,
            changepoints=self.changepoint.changepoints,
            n_changepoints=self.changepoint.n_changepoints,
            changepoint_range=self.changepoint.changepoint_range,
            changepoint_prior_scale=self.changepoint.changepoint_prior_scale
        )
        m.fit(df)
        future = m.make_future_dataframe(periods=self.number_of_days)
        forecast = m.predict(future)

        # Data at original scale
        forecast['yhat'] = np.exp(forecast['yhat'])
        forecast['yhat_upper'] = np.exp(forecast['yhat_upper'])
        forecast['yhat_lower'] = np.exp(forecast['yhat_lower'])
        df['y'] = np.exp(df['y'])

        if mara_prophet.config.forecast_table_name():
            self.insert_into_table(forecast)

        # Save model and forecasts dataframe as binaries in mara-db
        m_pickled = pickle.dumps(m)
        forecast_pickled = pickle.dumps(forecast)
        source_data_pickled = pickle.dumps(df)

        # Save hyper parameters used by the model as JSON in mara-db
        hyper_parameters = json.dumps({
            'growth': m.growth,
            'holidays': [d['ds'].strftime('%Y-%m-%d') for d in
                         m.holidays.to_dict('records')] if not m.holidays.empty else None,
            'changepoint_prior_scale': m.changepoint_prior_scale,
            'changepoint_range': m.changepoint_range,
            'changepoints': [cp.strftime('%Y-%m-%d') for cp in
                             m.changepoints.to_list()] if not m.changepoints.empty else None,
            'n_changepoints': m.n_changepoints,
            'seasonality_mode': m.seasonality_mode,
            'seasonality_prior_scale': m.seasonality_prior_scale,
            'yearly_seasonality': m.yearly_seasonality,
            'weekly_seasonality': m.weekly_seasonality,
            'daily_seasonality': m.daily_seasonality,
        })

        with mara_db.postgresql.postgres_cursor_context('mara') as cursor:
            cursor.execute(
                f"INSERT INTO forecasts(metric_name, forecast_ts, model, forecasts_df, source_df, hyper_parameters) "
                f"VALUES ({'%s, %s, %s, %s, %s, %s'})",
                (str(self.metric_name).lower().replace(' ', '_').replace('-', '_'),
                 datetime.datetime.utcnow(),
                 Binary(m_pickled),
                 Binary(forecast_pickled),
                 Binary(source_data_pickled),
                 hyper_parameters))


def create_forecast_table():
    """
    Drop and create the forecast table in mara and custom dbs
    """
    with mara_db.postgresql.postgres_cursor_context(mara_prophet.config.db_alias()) as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {mara_prophet.config.forecast_table_name()};"
                       f"CREATE TABLE {mara_prophet.config.forecast_table_name()} "
                       f"(metric_date DATE, metric_name TEXT, metric_value DOUBLE PRECISION,"
                       f"lower_ci DOUBLE PRECISION, upper_ci DOUBLE PRECISION );"
                       f"ALTER TABLE {mara_prophet.config.forecast_table_name()} "
                       f"ADD PRIMARY KEY (metric_date, metric_name) ")
    return True


def run_forecast(metric_name: str):
    """
    Runs a time-series analysis for a Forecast object
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
    forecast = None
    for f in mara_prophet.config.forecasts():
        if f.metric_name == metric_name:
            forecast = f
            break
    if forecast:
        logging.info('Running forecast for metric: ' + forecast.metric_name)
        logging.info('Number of days: ' + str(forecast.number_of_days))
        logging.info('Time series query: ' + forecast.time_series_query)
        forecast.forecast_metric()
    else:
        logging.warning('Oops, there is no defined forecast with name "{metric_name}".')
    return True
